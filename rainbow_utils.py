import re

# Colors were taken from here: https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
# TODO move into main
color_entries = list()
color_entries.append(('rainbow1', '#E6194B', None))
color_entries.append(('keyword.rainbow2', '#3CB44B', None))
color_entries.append(('entity.name.rainbow3', '#FFE119', None))
color_entries.append(('comment.rainbow4', '#0082C8', None))
color_entries.append(('string.rainbow5', '#FABEBE', None))
color_entries.append(('entity.name.tag.rainbow6', '#46F0F0', None))
color_entries.append(('storage.type.rainbow7', '#F032E6', None))
color_entries.append(('support.rainbow8', '#008080', None))
color_entries.append(('constant.language.rainbow9', '#F58231', None))
color_entries.append(('variable.language.rainbow10', '#FFFFFF', None))


# Taken from rbql_utils.py:
def split_quoted_str(src, dlm, preserve_quotes=False):
    assert dlm != '"'
    if src.find('"') == -1: # Optimization for majority of lines
        return (src.split(dlm), False)
    result = list()
    cidx = 0
    while cidx < len(src):
        if src[cidx] == '"':
            uidx = cidx + 1
            while True:
                uidx = src.find('"', uidx)
                if uidx == -1:
                    result.append(src[cidx:])
                    return (result, True)
                elif uidx + 1 == len(src) or src[uidx + 1] == dlm:
                    if preserve_quotes:
                        result.append(src[cidx:uidx + 1])
                    else:
                        result.append(src[cidx + 1:uidx].replace('""', '"'))
                    cidx = uidx + 2
                    break
                elif src[uidx + 1] == '"':
                    uidx += 2
                    continue
                else:
                    result.append(src[cidx:])
                    return (result, True)
        else:
            uidx = src.find(dlm, cidx)
            if uidx == -1:
                uidx = len(src)
            field = src[cidx:uidx]
            if field.find('"') != -1:
                result.append(src[cidx:])
                return (result, True)
            result.append(field)
            cidx = uidx + 1
    if src[-1] == dlm:
        result.append('')
    return (result, False)


def smart_split(src, dlm, policy, preserve_quotes):
    if policy == 'simple':
        return (src.split(dlm), False)
    return split_quoted_str(src, dlm, preserve_quotes)


def get_field_by_line_position(fields, query_pos):
    if not len(fields):
        return None
    col_num = 0
    cpos = len(fields[col_num]) + 1
    while query_pos > cpos and col_num + 1 < len(fields):
        col_num += 1
        cpos = cpos + len(fields[col_num]) + 1
    return col_num


def guess_if_header(potential_header, sampled_records):
    # Single line - not header
    if len(sampled_records) < 1:
        return False

    num_fields = len(potential_header)

    # Different number of columns - not header
    for sr in sampled_records:
        if len(sr) != num_fields:
            return False

    # All sampled lines do not have any letters in a column and potential header does - header
    optimistic_name_re = '^"?[a-zA-Z]{3,}'
    pessimistic_name_re = '[a-zA-Z]'
    for c in range(num_fields):
        if re.match(optimistic_name_re, potential_header[c]) is None:
            continue
        all_numbers = True
        for sr in sampled_records:
            if re.match(pessimistic_name_re, sr[c]) is not None:
                all_numbers = False
                break
        if all_numbers:
            return True

    return False


def generate_tab_statusline(tabstop_val, template_fields):
    # If separator is not tab, tabstop_val must be set to 1
    result = list()
    space_deficit = 0
    for nf in range(len(template_fields)):
        available_space = (1 + len(template_fields[nf]) // tabstop_val) * tabstop_val
        column_name = 'a{}'.format(nf + 1)
        extra_len = available_space - len(column_name) - 1
        if extra_len < 0:
            space_deficit += abs(extra_len)
            extra_len = 0
        else:
            regained = min(space_deficit, extra_len)
            space_deficit -= regained
            extra_len -= regained
        space_filling = ' ' * (1 + extra_len)
        if nf + 1 == len(template_fields):
            space_filling = ''
        result.append(column_name)
        result.append(space_filling)
    return result

