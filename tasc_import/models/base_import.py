import json
import operator
from odoo.addons.base_import.models.base_import import ImportValidationError,Import
from odoo import api, fields, models
from odoo.tools.translate import _

# class BaseImport(Import):

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
    for row in map(mapper, rows_to_import):
        if len(indices_analytic_distribution) > 0:
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
                        analytic_distributions += ',' + str(analytic_account.id)
                    else:
                        raise ImportValidationError(
                            _("Analytic distribution contains incorrect values"))
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

Import._convert_import_data=_convert_import_data

