import re
import math

# colors were taken from here: https://sashat.me/2017/01/11/list-of-20-simple-distinct-colors/
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


# taken from rbql_utils.py:
def split_quoted_str(src, dlm, preserve_quotes=False):
    assert dlm != '"'
    if src.find('"') == -1: #optimization for majority of lines
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
    # single line - not header
    if len(sampled_records) < 1:
        return False

    num_fields = len(potential_header)

    # different number of columns - not header
    for sr in sampled_records:
        if len(sr) != num_fields:
            return False

    # all sampled lines has a number in a column and potential header doesn't - header
    number_re = '^-?[0-9]+(?:[.,][0-9]+)?$'
    for c in range(num_fields):
        if re.match(number_re, potential_header[c]):
            continue
        all_numbers = True
        for sr in sampled_records:
            if not re.match(number_re, sr[c]):
                all_numbers = False
                break
        if all_numbers:
            return True

    # at least N columns 2 times longer than MAX or 2 times smaller than MIN - header
    required_extremes_count = 1 if num_fields <= 3 else int(math.ceil(num_fields * 0.333))
    found_extremes = 0
    for c in range(num_fields):
        minl = min([len(sr[c]) for sr in sampled_records])
        maxl = max([len(sr[c]) for sr in sampled_records])
        if len(potential_header[c]) > maxl * 2:
            found_extremes += 1
        if len(potential_header[c]) * 2 < minl:
            found_extremes += 1
    if found_extremes >= required_extremes_count:
        return True

    return False



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true', help='Run in verbose mode')
    parser.add_argument('--num_iter', type=int, help='number of iterations option')
    parser.add_argument('file_name', help='example of positional argument')
    args = parser.parse_args()

    num_iter = args.num_iter
    file_name = args.file_name

    for line in sys.stdin:
        line = line.rstrip('\n')
        fields = line.split('\t')


if __name__ == '__main__':
    main()
