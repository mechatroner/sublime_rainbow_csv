import re


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


def generate_tab_statusline(tabstop_val, template_fields, max_output_len=None):
    # If separator is not tab, tabstop_val must be set to 1
    result = list()
    space_deficit = 0
    cur_len = 0
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
        if max_output_len is not None and cur_len + len(column_name) > max_output_len:
            break
        result.append(column_name)
        result.append(space_filling)
        cur_len += len(column_name) + len(space_filling)
    if len(result):
        result[-1] = ''
    return result

