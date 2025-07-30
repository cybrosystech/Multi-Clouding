import json
import operator
import logging
from odoo import api, fields, models
from odoo.tools.translate import _
_logger = logging.getLogger(__name__)
from odoo.addons.base_import.models.base_import import ImportValidationError, Import


@api.model
def _convert_import_data(self, fields, options):
    """ Extracts the input BaseModel and fields list (with
        ``False``-y placeholders for fields to *not* import) into a
        format Model.import_data can use: a fields list without holes
        and the precisely matching data matrix

        :param list(str|bool): fields
        :returns: (data, fields)
        :rtype: (list(list(str)), list(str))
        :raises ValueError: in case the import data could not be converted
    """
    # Get indices for non-empty fields
    indices = [index for index, field in enumerate(fields) if field]
    if not indices:
        raise ImportValidationError(
            _("You must configure at least one field to import"))
    # If only one index, itemgetter will return an atom rather
    # than a 1-tuple
    if len(indices) == 1:
        mapper = lambda row: [row[indices[0]]]
    else:
        mapper = operator.itemgetter(*indices)
    # Get only list of actually imported fields
    import_fields = [f for f in fields if f]

    _file_length, rows_to_import = self._read_file(options)
    if len(rows_to_import[0]) != len(fields):
        raise ImportValidationError(
            _("Error while importing records: all rows should be of the same size, but the title row has %d entries while the first row has %d. You may need to change the separator character.",
              len(fields), len(rows_to_import[0]))
        )

    if options.get('has_headers'):
        rows_to_import = rows_to_import[1:]

    indices_analytic_distribution = []
    target_string = 'analytic_distribution'

    for i, string in enumerate(import_fields):
        if string == target_string:
            indices_analytic_distribution.append(i)
        elif '/' in string:
            parts = string.split('/')
            for part in parts[1:]:
                if part == target_string:
                    indices_analytic_distribution.append(i)
                    break

    data = []
    i = 0
    for row in map(mapper, rows_to_import):
        i += 1
        if len(indices_analytic_distribution) > 0:
            if not row[indices_analytic_distribution[0]] == '':
                data_dict = json.loads(row[indices_analytic_distribution[0]])
                new_dict = {}
                for key in data_dict:
                    val = data_dict.get(key)
                    split_keys = key.split(',')
                    analytic_distributions = ''
                    for account in split_keys:
                        analytic_account = self.env[
                            'account.analytic.account'].search(
                            [('name', '=', account)])
                        if analytic_account:
                            analytic_distributions += ',' + str(
                                analytic_account.id)
                        else:
                            raise ImportValidationError(
                                _("Analytic distribution contains incorrect values %s on row %d",
                                  row[indices_analytic_distribution[0]], i + 1))
                    new_dict.update({str(analytic_distributions): val})
                new_analytic_dist = json.dumps(new_dict)
                row = list(row)
                row[indices_analytic_distribution[0]] = new_analytic_dist
                row = tuple(row)
        data.append(list(row))
    # data = [
    #     list(row) for row in map(mapper, rows_to_import)
    #     # don't try inserting completely empty rows (e.g. from
    #     # filtering out o2m fields)
    #     if any(row)
    # ]

    # slicing needs to happen after filtering out empty rows as the
    # data offsets from load are post-filtering
    return data[options.get('skip'):], import_fields


def execute_import(self, fields, columns, options, dryrun=False):
    """ Actual execution of the import

    :param fields: import mapping: maps each column to a field,
                   ``False`` for the columns to ignore
    :type fields: list(str|bool)
    :param columns: columns label
    :type columns: list(str|bool)
    :param dict options:
    :param bool dryrun: performs all import operations (and
                        validations) but rollbacks writes, allows
                        getting as much errors as possible without
                        the risk of clobbering the database.
    :returns: A list of errors. If the list is empty the import
              executed fully and correctly. If the list is
              non-empty it contains dicts with 3 keys:

              ``type``
                the type of error (``error|warning``)
              ``message``
                the error message associated with the error (a string)
              ``record``
                the data which failed to import (or ``false`` if that data
                isn't available or provided)
    :rtype: dict(ids: list(int), messages: list({type, message, record}))
    """
    self.ensure_one()
    self._cr.execute('SAVEPOINT import')

    try:
        input_file_data, import_fields = self._convert_import_data(fields,
                                                                   options)
        # Parse date and float field
        input_file_data = self._parse_import_data(input_file_data,
                                                  import_fields, options)
    except ImportValidationError as error:
        return {'messages': [error.__dict__]}

    _logger.info('importing %d rows...', len(input_file_data))

    import_fields, merged_data = self._handle_multi_mapping(import_fields,
                                                            input_file_data)

    if options.get('fallback_values'):
        merged_data = self._handle_fallback_values(import_fields, merged_data,
                                                   options['fallback_values'])

    name_create_enabled_fields = options.pop('name_create_enabled_fields', {})
    import_limit = options.pop('limit', None)
    model = self.env[self.res_model].with_context(
        import_file=True,
        name_create_enabled_fields=name_create_enabled_fields,
        import_set_empty_fields=options.get('import_set_empty_fields', []),
        import_skip_records=options.get('import_skip_records', []),
        _import_limit=import_limit)
    import_result = model.load(import_fields, merged_data)
    record_ids = import_result.get('ids')
    if record_ids:
        records = model.browse(record_ids).filtered(
            lambda r: hasattr(r, 'message_post'))
        records.message_post(body="Record created/updated via import.")

    _logger.info('done')

    # If transaction aborted, RELEASE SAVEPOINT is going to raise
    # an InternalError (ROLLBACK should work, maybe). Ignore that.
    # TODO: to handle multiple errors, create savepoint around
    #       write and release it in case of write error (after
    #       adding error to errors array) => can keep on trying to
    #       import stuff, and rollback at the end if there is any
    #       error in the results.
    try:
        if dryrun:
            self._cr.execute('ROLLBACK TO SAVEPOINT import')
            # cancel all changes done to the registry/ormcache
            # we need to clear the cache in case any created id was added to an ormcache and would be missing afterward
            self.pool.clear_all_caches()
            # don't propagate to other workers since it was rollbacked
            self.pool.reset_changes()
        else:
            self._cr.execute('RELEASE SAVEPOINT import')
    except psycopg2.InternalError:
        pass

    # Insert/Update mapping columns when import complete successfully
    if import_result['ids'] and options.get('has_headers'):
        BaseImportMapping = self.env['base_import.mapping']
        for index, column_name in enumerate(columns):
            if column_name:
                # Update to latest selected field
                mapping_domain = [('res_model', '=', self.res_model),
                                  ('column_name', '=', column_name)]
                column_mapping = BaseImportMapping.search(mapping_domain,
                                                          limit=1)
                if column_mapping:
                    if column_mapping.field_name != fields[index]:
                        column_mapping.field_name = fields[index]
                else:
                    BaseImportMapping.create({
                        'res_model': self.res_model,
                        'column_name': column_name,
                        'field_name': fields[index]
                    })
    if 'name' in import_fields:
        index_of_name = import_fields.index('name')
        skipped = options.get('skip', 0)
        # pad front as data doesn't contain anythig for skipped lines
        r = import_result['name'] = [''] * skipped
        # only add names for the window being imported
        r.extend(x[index_of_name] for x in input_file_data[:import_limit])
        # pad back (though that's probably not useful)
        r.extend([''] * (len(input_file_data) - (import_limit or 0)))
    else:
        import_result['name'] = []

    skip = options.get('skip', 0)
    # convert load's internal nextrow to the imported file's
    if import_result['nextrow']:  # don't update if nextrow = 0 (= no nextrow)
        import_result['nextrow'] += skip

    return import_result


Import._convert_import_data = _convert_import_data
Import.execute_import = execute_import

