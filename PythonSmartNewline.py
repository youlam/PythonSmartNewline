import sublime
from sublime import Region
import sublime_plugin
import re
from itertools import chain


report = False


python_atomic_scopes = [
    'comment.line.number-sign.python',
    'entity.name.function.python',
    'punctuation.accessor.dot.python',
    'punctuation.definition.string.begin.python',
    'punctuation.definition.string.end.python',
    'punctuation.definition.comment.python',
    'punctuation.section.mapping-or-set.begin.python',
    'punctuation.separator.continuation.line.python',
    'punctuation.separator.arguments.python',
    'punctuation.separator.parameters.python',
    'punctuation.separator.sequence.python',
    'punctuation.section.arguments.begin.python',
    'punctuation.section.function.begin.python',
    'punctuation.section.group.begin.python',
    'punctuation.section.parameters.begin.python',
    'punctuation.section.parameters.end.python',
    'punctuation.section.brackets.end.python',
    'punctuation.section.brackets.begin.python',
    'keyword.control.flow.conditional.python',
    'keyword.control.flow.for.python',
    'keyword.control.flow.else.inline.python',
    'keyword.operator.assignment.python',
    'keyword.operator.assignment.augmented.python',
    'keyword.operator.logical.python',
    'keyword.operator.comparison.python',
    'keyword.other.assert.python',
    'keyword.control.import.from.python',
    'keyword.control.flow.return.python',
    'keyword.control.flow.for.in.python',
    'keyword.control.flow.break.python',
    'keyword.control.flow.raise.python',
    'storage.type.function.python',
    'string.quoted.double.python',
    'string.quoted.single.python',
    'support.type.exception.python',
    'support.type.python',
    'support.function.builtin.python',
    'variable.parameter.python'
]


python_certified_nonatomic_scopes = [
    'constant.language.python',
    'constant.numeric.integer.decimal.python',
    'keyword.control.import.python',                # (alas...)
    'meta.generic-name.python',
    'meta.statement.conditional.python',
    'meta.statement.if.python',
    'meta.statement.for.python',
    'meta.statement.raise.python',
    'meta.mapping.python',
    'meta.sequence.list.python',
    'punctuation.separator.tuple.python',
    'punctuation.section.block.conditional.python',
    'source.python',
    'storage.type.function.python'
]

python_group_scopes = [
    'meta.function-call.arguments.python',
    'meta.sequence.list.python',
    'meta.mapping-or-set.python',
    'meta.group.python'
]

python_closing_group_scopes = {
    'punctuation.section.arguments.end.python':  {'punctuation.section.arguments.begin.python'},
    'punctuation.section.brackets.end.python':   {'punctuation.section.brackets.begin.python'},
    'punctuation.section.group.end.python':      {'punctuation.section.group.begin.python'},
    'punctuation.section.interpolation.end.python': {'punctuation.section.interpolation.begin.python'},
    'punctuation.section.mapping.end.python':    {'punctuation.section.mapping-or-set.begin.python',
                                                  'punctuation.section.mapping.begin.python'},
    'punctuation.section.parameters.end.python': {'punctuation.section.parameters.begin.python'},
    'punctuation.section.sequence.end.python':   {'punctuation.section.sequence.begin.python'},
    'punctuation.section.set.end.python':        {'punctuation.section.mapping-or-set.begin.python',
                                                  'punctuation.section.set.begin.python'},
    'punctuation.section.mapping-or-set.end.python': {'punctuation.section.mapping-or-set.begin.python',
                                                      'punctuation.section.set.begin.python',
                                                      'punctuation.section.mapping.begin.python'}
}

python_opening_group_scopes = {
    'punctuation.section.arguments.begin.python',
    'punctuation.section.brackets.begin.python',
    'punctuation.section.group.begin.python',
    'punctuation.section.interpolation.begin.python',
    'punctuation.section.mapping.begin.python',
    'punctuation.section.mapping-or-set.begin.python',
    'punctuation.section.parameters.begin.python',
    'punctuation.section.sequence.begin.python',
    'punctuation.section.set.begin.python'
}

python_comma_scopes = {
    'punctuation.separator.arguments.python',
    'punctuation.separator.parameters.python',
    'punctuation.separator.sequence.python'
}

python_colon_scopes = [
    'punctuation.section.block.conditional.python',
    'punctuation.section.block.except.python',
    'punctuation.section.block.for.python',
    'punctuation.section.block.try.python',
    'punctuation.section.block.while.python',
    'punctuation.section.block.with.python',
    'punctuation.section.block.python',
    'punctuation.section.function.begin.python',
    'meta.statement.for.python',
    'meta.statement.except.python',
    'meta.statement.try.python',
    'meta.statement.with.python'
]


def comb_view_for_scope(view, scope_name):
    pt = 0
    while pt < view.size():
        s = scope_as_array(view, pt)
        if scope_name in s:
            break

        extended = Region(pt)
        if s[-1] in python_atomic_scopes:
            extended = view.extract_scope(pt)

        pt = extended.end() if extended.end() > pt else pt + 1

    if pt < view.size():
        row_no, col_no = view.rowcol(pt)
        message = "scope " + str(scope_name) + " found at row, col: " + str(row_no) + ", " + str(col_no)

        if report:
            print(message)
            show_scope(view, pt, "comb_view_for_scope")


def last_index_of(some_list, some_element):
    try:
        return len(some_list) - 1 - some_list[::-1].index(some_element)

    except ValueError:
        return -1


def last_index_of_not_followed_by(some_list, element, follower_or_followers):
    if isinstance(follower_or_followers, list) or \
       isinstance(follower_or_followers, tuple):
        followers = follower_or_followers

    else:
        followers = [follower_or_followers]

    assert all(isinstance(x, str) for x in followers)

    li = -1
    for index, (el, next_el) in enumerate(zip(some_list, chain(some_list[1:], [None]))):
        if el == element and next_el not in followers:
            li = index

    return li


def last_index_among(some_list, some_elements):
    to_return = -1
    for s in some_elements:
        to_return = max(to_return, last_index_of(some_list, s))
    return to_return


def last_index_among_not_followed_by(some_list, some_tuples):
    to_return = -1
    for s in some_tuples:
        assert len(s) == 2
        to_return = max(to_return, last_index_of_not_followed_by(some_list, s[0], s[1]))
    return to_return


def exists_any_not_followed_by(some_list, some_tuples):
    for index, (el, next_el) in enumerate(zip(some_list, chain(some_list[1:], [None]))):
        if any(el == t[0] and next_el != t[1] for t in some_tuples):
            return True
    return False


def exists_not_followed_by_any(some_list, element, followers):
    for i, thing in enumerate(some_list):
        if thing == element and \
           (
               i == len(some_list) - 1 or
               some_list[i] not in followers
           ):
            return True
    return False


def exists_not_followed_by(some_list, element, follower):
    return last_index_of_not_followed_by(some_list, element, follower) >= 0


def move_to_eol(view, extend=False):
    view.run_command("move_to", {"to": "eol", "extend": extend})


def generic_line_regions_from_line_no(view, row):
    pt = view.text_point(row, 0)
    return generic_line_regions_from_pt(view, pt)


def generic_line_regions_from_pt(view, pt):
    line = view.line(pt)
    line_string = view.substr(line)

    i = 0
    while i < len(line_string) and line_string[i] == ' ':
        i += 1

    if i < len(line_string):
        j = 0
        while j < len(line_string) and line_string[-1 - j] == ' ':
            j += 1
        assert i + j < len(line_string)
        assert line.begin() + i < line.end() - j
        source = Region(line.begin() + i, line.end() - j)

    else:
        j = 0
        source = None

    return line, source


def python_line_regions_from_pt(view, pt):
    line = view.line(pt)
    line_string = view.substr(line)
    eol_scope = scope_as_array(view, line.end())

    # comment region computation
    comment_region = None
    source_end = line.end() - line.begin()
    if eol_scope[-1] == 'comment.line.number-sign.python':
        comment_region = view.extract_scope(line.end())
        comment_region = Region(max(line.begin(), comment_region.begin()),
                                min(line.end(), comment_region.end()))
        assert line.begin() <= comment_region.begin() <= line.end() - 1
        source_end = comment_region.begin() - line.begin()

    # source end (end of) computation
    if 'meta.string.python' not in scope_as_array(view, line.begin() + source_end):
        while source_end > 0:
            if line_string[source_end - 1] != ' ':
                break
            source_end -= 1
    source_end += line.begin()

    # source begin computation
    source_begin = 0
    while source_begin < len(line_string):
        if line_string[source_begin] != ' ':
            break
        source_begin += 1
    source_begin += line.begin()

    source_region = None
    if source_begin < source_end:
        source_region = Region(source_begin, source_end)

    return line, source_region, comment_region


def python_line_regions_from_line_no(view, row):
    return python_line_regions_from_pt(view, view.text_point(row, 0))


def vanilla_newline_insert_at_pt(view, edit, pt, where):
    line = view.line(pt)

    if where == 'bol':
        pt = line.begin()
    elif where == 'eol':
        pt = line.end()
    else:
        assert where == 'here'

    view.insert(edit, pt, '\n')
    row, col = view.rowcol(pt)
    next_line = view.line(view.text_point(row + 1, 0))

    assert next_line.size() == line.end() - pt
    assert next_line.begin() == pt + 1

    return Region(pt + 1)


def python_basic_newline_insert_at_pt(view, edit, pt):
    regions = view.sel()
    assert regions.contains(Region(pt))
    view.insert(edit, pt, '\n')


def python_basic_newline_insert(view, edit, hard):
    regions = view.sel()
    if not hard:
        move_to_eol(view)
    for r in regions:
        assert r.size() == 0
        view.insert(edit, r.begin(), '\n')
        line, source, comment = python_line_regions_from_pt(view, r.begin() + 1)
        z = source.begin() if source else (comment.begin() if comment else line.end())
        if z > line.begin():
            view.erase(edit, Region(line.begin(), z))


def python_if_analysis(view, edit, pt):
    line, source, _ = python_line_regions_from_pt(view, pt)

    inline_else_pt = None
    if_pt = None
    if_source_begin = None

    while True:
        if pt < source.begin():
            pt = line.begin() - 1
            if pt < 0:
                if report:
                    print("breaking pt -1")
                break
            line, source, comment = python_line_regions_from_pt(view, pt)
            if comment is not None:
                pt = comment.begin() - 1
            if source is None:
                if report:
                    print("breaking pt 0")
                break
            assert pt >= source.begin()

        pt_scope = scope_as_array(view, pt)
        if 'meta.statement.if.python' not in pt_scope:
            if report:
                print("breaking pt 1; pt", pt)
                print("line:", view.substr(line))
            break

        extended = view.extract_scope(pt)

        if pt_scope[-1] == 'keyword.control.flow.else.inline.python':
            if view.substr(extended).endswith('else'):
                inline_else_pt = extended.end() - 4

            else:
                assert False

            assert inline_else_pt - 1 < pt

            pt = inline_else_pt - 1
            continue

        if pt_scope[-1] == 'keyword.control.flow.conditional.python' and \
           pt <= extended.begin() + 1 and \
           view.substr(Region(extended.begin(), extended.begin() + 2)) == 'if':
            if_pt = extended.begin()
            if_source_begin = source.begin()
            if report:
                print("breaking pt 2")
            break

        if pt_scope[-1] in python_closing_group_scopes:
            beginning = python_beginning_of_scope_attached_to_closing_group(view, edit, pt)
            if beginning is None:
                if report:
                    print("breaking pt 3")
                break
            assert beginning < pt
            pt = beginning
            continue

        if pt_scope[-1] in python_atomic_scopes:
            pt = min(pt - 1, extended.begin())
            continue

        pt -= 1

    return if_source_begin, if_pt, inline_else_pt


def python_intervening_inline_else(view, line, source_region):
    pt = source_region.end() - 1

    while pt > source_region.begin():
        a = scope_as_array(view, pt)
        show_scope(view, pt, "python_intervening_inline_else")
        if 'keyword.control.flow.else.inline.python' in a:
            return True
        if a[-1] in python_atomic_scopes:
            extended = view.extract_scope(pt)
            if extended.begin() < pt:
                pt = extended.begin()
            else:
                pt -= 1
        else:
            pt -= 1

    return False


def python_find_if_matching_indent_starting_from_line_no(view, line_no):
    line, source, comment = python_line_regions_from_line_no(view, line_no)
    assert source is not None
    ze_indent = source.begin() - line.begin()
    a = scope_as_array(view, source.begin())
    assert a == ['source.python', 'meta.statement.conditional.python', 'keyword.control.flow.conditional.python']

    l = line_no - 1

    while l >= 0:
        line, source, comment = python_line_regions_from_line_no(view, l)
        if source:
            indent = source.begin() - line.begin()
            if indent < ze_indent:
                return None
            if indent == ze_indent:
                a = scope_as_array(view, source.begin())
                if a == ['source.python', 'meta.statement.if.python', 'keyword.control.flow.conditional.python']:
                    return l
                if a != ['source.python', 'meta.statement.conditional.python', 'keyword.control.flow.conditional.python']:
                    return None
        l -= 1

    return None


def python_find_logical_indent_for_else_elif(view, line_no):
    line, source, comment = python_line_regions_from_line_no(view, line_no)
    assert source is not None
    a = scope_as_array(view, source.begin())
    assert a == ['source.python', 'meta.statement.conditional.python', 'keyword.control.flow.conditional.python']

    ze_indent = source.begin() - line.begin()

    l = line_no - 1

    while l >= 0:
        line, source, comment = python_line_regions_from_line_no(view, l)
        if source:
            indent = source.begin() - line.begin()
            if indent <= ze_indent:
                a = scope_as_array(view, source.begin())
                if a == ['source.python', 'meta.statement.if.python', 'keyword.control.flow.conditional.python']:
                    return indent
                if a == ['source.python', 'meta.statement.conditional.python', 'keyword.control.flow.conditional.python']:
                    string = view.substr(source)
                    if string.startswith('elif') or string.startswith('else if'):
                        return indent
                    if string.startswith('else'):
                        line_with_matching_if = python_find_if_matching_indent_starting_from_line_no(view, l)
                        if line_with_matching_if is None:
                            return None
                        assert line_with_matching_if < l
                        l = line_with_matching_if - 1
                        continue
                    assert False
        l -= 1

    return None


def python_find_try_matching_indent_starting_from_line_no(view, line_no):
    line, source, comment = python_line_regions_from_line_no(view, line_no)
    assert source is not None
    ze_indent = source.begin() - line.begin()
    a = scope_as_array(view, source.begin())
    assert a == ['source.python', 'meta.statement.except.python', 'keyword.control.flow.except.python']

    l = line_no - 1

    while l >= 0:
        line, source, comment = python_line_regions_from_line_no(view, l)
        if source:
            indent = source.begin() - line.begin()
            if indent < ze_indent:
                return None
            if indent == ze_indent:
                a = scope_as_array(view, source.begin())
                if a == ['source.python', 'meta.statement.try.python', 'keyword.control.flow.try.python']:
                    return l
                return None
        l -= 1

    return None


def python_find_logical_indent_for_except(view, line_no):
    line, source, comment = python_line_regions_from_line_no(view, line_no)
    assert source is not None
    a = scope_as_array(view, source.begin())
    assert a == ['source.python', 'meta.statement.except.python', 'keyword.control.flow.except.python']

    ze_indent = source.begin() - line.begin()

    l = line_no - 1

    while l >= 0:
        line, source, comment = python_line_regions_from_line_no(view, l)
        if source:
            indent = source.begin() - line.begin()
            if indent <= ze_indent:
                a = scope_as_array(view, source.begin())
                if a == ['source.python', 'meta.statement.try.python', 'keyword.control.flow.try.python']:
                    return indent
                if a == ['source.python', 'meta.statement.except.python', 'keyword.control.flow.except.python']:
                    line_with_matching_if = python_find_try_matching_indent_starting_from_line_no(view, l)
                    if line_with_matching_if is None:
                        return None
                    assert line_with_matching_if < l
                    l = line_with_matching_if - 1
                    continue
        l -= 1


def is_some_kind_of_group_scope(scope):
    if exists_any_not_followed_by(
        scope,
        [
            ('meta.group.python', 'punctuation.section.group.begin'),
            ('meta.function-call.arguments.python', 'punctuation.section.arguments.begin.python'),
            ('meta.mapping.python', 'punctuation.section.mapping.begin.python'),
            ('meta.sequence.list.python', 'punctuation.section.sequence.begin.python'),
            ('meta.mapping.empty.python', 'punctuation.section.mapping.begin.python'),
            ('meta.set.python', 'punctuation.section.set.begin.python'),
            ('meta.function.parameters.python', 'punctuation.section.parameters.begin.python')
        ]
    ):
        return True

    if exists_not_followed_by_any(
        scope,
        'meta.item-access.python',
        ['punctuation.section.brackets.begin.python', 'meta.qualified-name.python']
    ):
        return True

    return False


def is_at_beginning_or_after_end_of_string(view, pt, pt_scope=None):
    if pt_scope is None:
        pt_scope = scope_as_array(view, pt)

    if exists_any_not_followed_by(
        pt_scope,
        [
            ('string.quoted.single.python', 'punctuation.definition.string.begin.python'),
            ('string.quoted.double.python', 'punctuation.definition.string.begin.python'),
            ('string.quoted.single.block.python', 'punctuation.definition.string.begin.python'),
            ('string.quoted.double.block.python', 'punctuation.definition.string.begin.python')
        ]
    ):
        return False

    if 'string.quoted.double.block.python' in pt_scope or \
       'string.quoted.single.block.python' in pt_scope:
        pp_pt_scope = scope_as_array(view, pt + 1)

        if not exists_any_not_followed_by(
            pp_pt_scope,
            [
                ('string.quoted.double.block.python', 'punctuation.definition.string.begin.python'),
                ('string.quoted.single.block.python', 'punctuation.definition.string.begin.python')
            ]
        ):
            return False

        pp_pp_pt_scope = scope_as_array(view, pt + 2)

        if not exists_any_not_followed_by(
            pp_pp_pt_scope,
            [
                ('string.quoted.double.block.python', 'punctuation.definition.string.begin.python'),
                ('string.quoted.single.block.python', 'punctuation.definition.string.begin.python')
            ]
        ):
            return False

    return True


def is_inside_string_or_comment(view, pt, pt_scope=None):
    if pt_scope is None:
        pt_scope = scope_as_array(view, pt)

    if pt_scope[-1] == 'punctuation.section.interpolation.begin.python':
        return True

    if 'comment.block.documentation.python' in pt_scope:
        if 'punctuation.definition.comment.begin.python' not in pt_scope:
            return True

        if 'punctuation.definition.comment.begin.python' not in scope_as_array(view, pt + 1):
            return True

        if 'punctuation.definition.comment.begin.python' not in scope_as_array(view, pt + 2):
            return True

        return False

    if is_at_beginning_or_after_end_of_string(view, pt, pt_scope):
        return False

    if 'invalid.illegal.empty-expression.python' in pt_scope and \
       'meta.string.interpolated.python' in pt_scope and \
       '{' != view.substr(Region(pt, pt + 1)):
        return False

    i1 = last_index_among_not_followed_by(
        pt_scope,
        [
            ('string.quoted.single.python', 'punctuation.definition.string.begin.python'),
            ('string.quoted.double.python', 'punctuation.definition.string.begin.python'),
            ('string.quoted.single.block.python', 'punctuation.definition.string.begin.python'),
            ('string.quoted.double.block.python', 'punctuation.definition.string.begin.python')
        ]
    )

    # there's some but with the scopes for f-type block strings :( :( so we couldn't assert this:
    # assert i1 > 0

    i2 = last_index_among(pt_scope, ['source.python.embedded'])

    if i2 > i1:
        return False

    return True


def python_prepare_newline_at_pt(view, edit, pt, restorative):

    def reset_pt_scope():
        nonlocal pt_scope, pt_prev_scope, pt_4_pt_prev_scope
        assert line.begin() <= pt <= line.end()
        pt_scope = scope_as_array(view, pt)

        j = 1
        while pt - j >= line.begin() and view.substr(Region(pt - j, pt - j + 1)) == ' ':
            j += 1

        pt_prev_scope = ['']
        pt_4_pt_prev_scope = None
        if pt - j > line.begin():
            pt_4_pt_prev_scope = pt - j
            pt_prev_scope = scope_as_array(view, pt - j)

    def reset_source_scopes():
        nonlocal source_begin_scope, source_end_scope, source_end_prev_scope
        assert source is not None
        source_begin_scope = scope_as_array(view, source.begin())
        source_end_scope = scope_as_array(view, source.end())
        source_end_prev_scope = scope_as_array(view, source.end() - 1)

    def reset_basics():
        nonlocal line, source, comment, source_str
        line, source, comment = python_line_regions_from_pt(view, line.begin() if line else pt)
        assert line.begin() <= pt <= line.end()
        reset_pt_scope()
        if source:
            source_str = view.substr(source)
            reset_source_scopes()
        assert line.begin() <= pt <= line.end()
        assert not pt_is_region_mode or regions.contains(Region(pt))
        assert len(regions) <= original_num_regions

    def move_pt_to(val):
        nonlocal pt
        assert line.begin() <= val <= line.end()
        if pt_is_region_mode:
            regions.subtract(Region(pt))
            regions.add(Region(val))
        pt = val
        reset_basics()

    def erase(r):
        nonlocal pt
        view.erase(edit, r)
        if r.begin() < pt < r.end():
            pt = r.begin()
            if pt_is_region_mode:
                regions.add(Region(pt))
        elif pt >= r.end():
            pt -= r.size()
        reset_basics()

    def insert(material, q):
        nonlocal pt
        assert line.begin() <= q <= line.end()
        view.insert(edit, q, material)
        if pt >= q:
            pt += len(material)
        reset_basics()

    def line_end_trim_whitespace():
        max_let = comment.end() if comment else (source.end() if source else line.begin())
        if max_let < line.end():
            erase(Region(max_let, line.end()))

    def adjust_pre_comment_space():
        assert comment

        if original_source_end and \
           original_comment_begin - original_source_end == 2:
            desired_comment_begin = source.end() + 2

        else:
            if source:
                desired_comment_begin = original_comment_begin

            else:
                desired_comment_begin = comment.begin()

        if source:
            new_comment_begin = max(desired_comment_begin, source.end() + 2)

        else:
            new_comment_begin = desired_comment_begin

        if new_comment_begin > comment.begin():
            insert(' ' * (new_comment_begin - comment.begin()), comment.begin())

        elif new_comment_begin < comment.begin():
            erase(Region(new_comment_begin, comment.begin()))

    def left_trim_whitespace():
        nonlocal pt
        if True or not any('string' in s for s in pt_scope):
            w = pt
            while w > line.begin() and view.substr(Region(w - 1, w)) == ' ':
                w -= 1
            if w < pt:
                erase(Region(w, pt))

    def move_left_past_whitespace_in_string():
        nonlocal pt
        if any('string' in s for s in pt_scope):
            w = pt
            while w > line.begin() and view.substr(Region(w - 1, w)) == ' ':
                w -= 1
            move_pt_to(w)

    def right_trim_whitespace(just_one=False):
        nonlocal pt
        # if not pt_scope[-1].startswith('string'):
        if not is_inside_string_or_comment(view, pt, pt_scope):
            w = pt
            while w < line.end() and view.substr(Region(w, w + 1)) == ' ':
                w += 1
                if just_one:
                    break
            if w > pt:
                erase(Region(pt, w))

    regions = view.sel()
    original_num_regions = len(regions)
    line_no, _ = view.rowcol(pt)
    pt_is_region_mode = regions.contains(Region(pt))
    if not pt_is_region_mode:
        assert restorative

    line = None
    source = None
    comment = None
    pt_scope = None
    pt_prev_scope = None
    pt_4_pt_prev_scope = None
    source_end_scope = None
    source_begin_scope = None
    source_end_prev_scope = None

    reset_basics()

    original_comment_begin = comment.begin() if comment else None
    original_source_end = source.end() if source else None

    # line_end_trim_whitespace()
    if not restorative and \
       is_at_beginning_or_after_end_of_string(view, pt, pt_scope):
        insert(' ', pt)
        move_pt_to(pt - 1)

    # should we out-indent?
    if source or comment:
        content_start = source.begin() if source else comment.begin()

        if line.begin() > 0:
            indent, indent_type = python_indent_for_newline_at_pt(view, edit, line.begin() - 1)

            if content_start > line.begin() + indent:
                erase(Region(line.begin() + indent, content_start))

            elif (content_start < line.begin() + indent and
                  (indent_type.startswith('a1') or
                   indent_type.startswith('b1') or
                   indent_type.startswith('b2'))):
                amount = line.begin() + indent - content_start
                insert(' ' * amount, content_start)

    if source:
        # replace 'else if' by 'elif'
        if 'meta.statement.conditional.python' in source_begin_scope and \
           source.size() >= len('else if') and \
           view.substr(Region(source.begin(), source.begin() + 8)) == 'else if ' and \
           not any('string' in x for x in source_begin_scope):
            erase(Region(source.begin(), source.begin() + 7))
            insert('elif ', source.begin())

        # indentation of 'else', etc
        if source_begin_scope == ['source.python', 'meta.statement.conditional.python', 'keyword.control.flow.conditional.python'] and \
           (restorative or pt >= source.begin() + 4):
            logical_indent = python_find_logical_indent_for_else_elif(view, line_no)
            if logical_indent is not None:
                dif = (source.begin() - line.begin()) - logical_indent
                assert dif >= 0
                if dif > 0:
                    erase(Region(line.begin(), line.begin() + dif))

        # indentation of 'except'
        if source_begin_scope == ['source.python', 'meta.statement.except.python', 'keyword.control.flow.except.python'] and \
           (restorative or pt >= source.begin() + 6):
            logical_indent = python_find_logical_indent_for_except(view, line_no)
            if logical_indent is not None:
                dif = (source.begin() - line.begin()) - logical_indent
                assert dif >= 0
                if dif > 0:
                    erase(Region(line.begin(), line.begin() + dif))

        # characters beyond break
        if source_begin_scope[-1] == 'keyword.control.flow.break.python' and \
           source.begin() + 5 < source.end() and \
           (restorative or pt >= source.begin() + 5):
            erase(Region(source.begin() + 5, source.end()))

        # removing unnecessary '\'
        if (
            (restorative or pt >= source.end()) and
            'punctuation.separator.continuation.line.python' in source_end_prev_scope and
            any(x in source_end_scope for x in python_group_scopes)
        ):
            erase(Region(source.end() - 1, source.end()))

        # miscellaneous adding of space
        # AND adding ',' between arguments
        if 'punctuation.separator.continuation.line.python' in source_end_prev_scope and \
           view.substr(Region(source.end() - 2, source.end() - 1)) != ' ':
            insert(' ', source.end() - 1)

        paren_alpha = re.compile(r"['\)\]][A-Za-z_0-9]")
        comma_alpha = re.compile(r",[A-Za-z0-9_\[({]")
        number_alpha = re.compile(r" (-)?[0-9]+[A-Za-ik-z_]")
        comparison_alpha = re.compile(r"[<>=][A-Za-z_0-9]")
        alpha_space = re.compile(r"(?<=[A-Za-z0-9_\)\]}])[ ]+[A-Za-z0-9_\(\[]")
        quote_alpha = re.compile(r"\"[ief+*]")

        restart = True
        while restart:
            restart = False
            source_str = view.substr(source)

            for match in quote_alpha.finditer(source_str):
                if match is not None:
                    u = source.begin() + match.span()[0]
                    u_scope = scope_as_array(view, u)

                    if u_scope[-1] == 'punctuation.definition.string.end.python':
                        insert(' ', u + 1)
                        restart = True
                        break

            for match in alpha_space.finditer(source_str):
                if match is not None:
                    u = source.begin() + match.span()[0]
                    if view.substr(Region(u, u + 1)) != ' ':
                        print("source_str:", source_str)
                        print("match.span()[0]:", match.span()[0])
                    assert view.substr(Region(u, u + 1)) == ' '
                    u_scope = scope_as_array(view, u)

                    if u_scope[-1] in [
                        'meta.function-call.arguments.python',
                        'meta.function.parameters.python'
                    ]:
                        w = u + 1
                        while view.substr(Region(w, w + 1)) == ' ':
                            w += 1
                        if not scope_as_array(view, u - 1)[-1].startswith('keyword') and \
                           not scope_as_array(view, w)[-1].startswith('keyword'):
                            insert(',', u)
                            restart = True
                            break

            for match in paren_alpha.finditer(source_str):
                if match is not None:
                    u = source.begin() + match.span()[0]
                    u_scope = scope_as_array(view, u)
                    if (u_scope[-1] in python_closing_group_scopes or
                        u_scope[-1] == 'punctuation.definition.string.end.python') and \
                       'comment.block.documentation.python' not in u_scope:
                        insert(' ', u + 1)
                        restart = True
                        break

            for match in comma_alpha.finditer(source_str):
                if match is not None:
                    u = source.begin() + match.span()[0]
                    u_scope = scope_as_array(view, u)
                    if (u_scope[-1] in python_comma_scopes or
                        'string' not in u_scope or
                        'punctuation.definition.string.begin.python' in u_scope) and \
                       'comment.block.documentation.python' not in u_scope:
                        insert(' ', u + 1)
                        restart = True
                        break

            for match in number_alpha.finditer(source_str):
                if match is not None:
                    u = source.begin() + match.span()[1] - 1
                    u_scope = scope_as_array(view, u)
                    if 'string' not in u_scope and \
                       'comment.block.documentation.python' not in u_scope:
                        insert(' ', u)
                        restart = True
                        break

            for match in comparison_alpha.finditer(source_str):
                if match is not None:
                    u = source.begin() + match.span()[0]
                    u_scope = scope_as_array(view, u)
                    if u_scope[-1] == 'keyword.operator.comparison.python':
                        insert(' ', u + 1)
                        restart = True
                        break

        # adding inferred ' \'
        if restorative or pt >= source.end():
            if (
                (source_end_scope == ['source.python'] or
                 source_end_scope == ['source.python', 'meta.statement.conditional.python']) and
                ('keyword.operator.logical.python' in pt_prev_scope or
                 'keyword.operator.arithmetic.python' in pt_prev_scope or
                 'keyword.operator.assignment.python' in pt_prev_scope or
                 'keyword.operator.assignment.augmented.python' in pt_prev_scope)
            ) or (
                source_end_scope == ['source.python'] and
                view.substr(Region(source.end() - 1, source.end())) == ','
            ) or (
                source_end_prev_scope == ['source.python', 'keyword.other.assert.python']
            ):
                insert(' \\', source.end())

        else:
            if (
                ('keyword.operator.logical.python' in pt_prev_scope or
                 'keyword.operator.arithmetic.python' in pt_prev_scope or
                 'keyword.operator.assignment.python' in pt_prev_scope or
                 'keyword.operator.assignment.augmented.python' in pt_prev_scope or
                 'keyword.other.assert.python' in pt_prev_scope or
                 'keyword.control.flow.return.python'in pt_prev_scope) and
                not is_some_kind_of_group_scope(pt_scope)
            ):
                insert(' \\', pt_4_pt_prev_scope + 1)

        # removing '\' in favor of opening a group
        if (
            (restorative or pt >= source.end()) and
            source_begin_scope == ['source.python', 'meta.statement.conditional.python', 'keyword.control.flow.conditional.python'] and
            'punctuation.separator.continuation.line.python' in source_end_prev_scope
        ):
            if view.substr(Region(source.begin(), source.begin() + 4)) == 'elif':
                erase(Region(source.end() - 1, source.end()))
                insert('(', source.begin() + 5)

            elif view.substr(Region(source.begin(), source.begin() + 7)) == 'else if':
                erase(Region(source.end() - 1, source.end()))
                insert('(', source.begin() + 8)

        # opening a group because immediately after 'if' 'elif', 'else if'
        if (
            pt >= source.end() and
            (source_end_prev_scope[-1] == 'keyword.control.flow.conditional.python' or
             source_end_prev_scope[-1] == 'meta.statement.conditional.python') and
            view.substr(source) in ['if', 'elif', 'else if']
        ):
            insert(' ()', source.end())
            move_pt_to(source.end() - 1)

        # adding ',' to source_end
        if not restorative and \
           pt >= source.end() and \
           source_end_scope[-1] in [
               'meta.function.parameters.python',
               'meta.sequence.list.python',
               'meta.function-call.arguments.python',
               'meta.mapping-or-set.python',
               'meta.mapping.value.python',
               'meta.set.python'
           ] and source_end_prev_scope[-1] not in [
               'punctuation.section.arguments.begin.python',
               'punctuation.section.sequence.begin.python',
               'punctuation.sequence.python',
               'punctuation.separator.arguments.python',
               'punctuation.separator.parameters.python',
               'punctuation.separator.sequence.python',
               'punctuation.separator.set.python'
           ] and not source_end_prev_scope[-1].startswith('keyword'):
            insert(',', source.end())

        if not restorative and \
           pt >= source.end() and \
           source_end_scope[-1] in [
               'meta.group.python'
           ] and source_end_prev_scope[-1] not in [
               'punctuation.separator.tuple.python',
               'keyword.operator.logical.python',
               'keyword.operator.arithmetic.python',
               'punctuation.section.group.begin.python'
           ]:
            insert(',', source.end())

        # adding ',' at pt
        if (
            not restorative and
            pt < source.end() and
            (
                pt_scope[-1] in [
                    'meta.function.parameters.python',
                    'meta.sequence.list.python',
                    'meta.function-call.arguments.python',
                    'meta.mapping.value.python'
                ]
            ) and (
                pt_prev_scope[-1] not in [
                    'punctuation.section.arguments.begin.python',
                    'punctuation.section.sequence.begin.python',
                    'punctuation.sequence.python',
                    'punctuation.separator.arguments.python',
                    'punctuation.separator.parameters.python',
                    'punctuation.separator.sequence.python',
                    'punctuation.separator.set.python'
                ]
            ) and not pt_prev_scope[-1].startswith('keyword')
        ):
            u = pt
            while view.substr(Region(u, u + 1)) == ' ':
                u += 1
            if scope_as_array(view, u)[-1] not in [
                'punctuation.section.sequence.end.python',
                'punctuation.section.group.end.python',
                'punctuation.section.arguments.end.python'
            ]:
                left_trim_whitespace()
                insert(',', pt)

            else:
                u_start = python_beginning_of_scope_attached_to_closing_group(view, edit, u)
                if u_start is not None:
                    _, u_start_source, _ = python_line_regions_from_pt(view, u_start)
                    if u_start < u_start_source.end() - 1:
                        left_trim_whitespace()
                        insert(',', pt)

        if not restorative and \
           pt < source.end() and \
           (
               pt_scope[-1] in [
                   'meta.group.python'
               ]
           ) and pt_prev_scope[-1] not in [
               'punctuation.separator.tuple.python',
               'keyword.operator.logical.python',
               'keyword.operator.arithmetic.python',
               'punctuation.section.group.begin.python'
           ]:
            u = pt
            while view.substr(Region(u, u + 1)) == ' ':
                u += 1
            if scope_as_array(view, u)[-1] not in [
                'punctuation.section.sequence.end.python',
                'punctuation.section.group.end.python',
                'punctuation.section.arguments.end.python'
            ]:
                left_trim_whitespace()
                insert(',', pt)

        if not restorative and \
           pt < source.end() and \
           view.substr(Region(pt, pt + 2)) == ' )' and \
           (
               scope_as_array(view, pt + 1)[-3:] == ['meta.sequence.list.python', 'meta.group.python', 'punctuation.section.group.end.python'] or
               scope_as_array(view, pt + 1)[-3:] == ['meta.sequence.list.python', 'meta.sequence.tuple.python', 'punctuation.section.sequence.end.python']
           ):
            u = pt + 1
            u_start = python_beginning_of_scope_attached_to_closing_group(view, edit, u)
            if u_start is not None:
                _, u_start_source, _ = python_line_regions_from_pt(view, u_start)
                if u_start < u_start_source.end() - 1:
                    left_trim_whitespace()
                    insert(',', pt)

        # closing a group in absence of binary operator
        if (
            (restorative or pt >= source.end()) and
            source_end_scope[-1] == 'meta.group.python' and
            'keyword.operator.logical.python' not in source_end_prev_scope and
            'keyword.operator.arithmetic.python' not in source_end_prev_scope and
            'punctuation.section.group.begin.python' not in source_end_prev_scope and
            'punctuation.separator.tuple.python' not in source_end_prev_scope
        ):
            insert(')', source.end())

            matching = python_beginning_of_scope_attached_to_closing_group(view, edit, source.end() - 1)
            if matching is None:
                erase(Region(source.end() - 1, source.end()))

            else:
                l, s, c = python_line_regions_from_pt(view, matching)
                assert s is not None and s.begin() <= matching < s.end()
                # if matching dude is at end of its line, we want to drag it to next line with us:
                if matching == s.end() - 1:
                    move_pt_to(source.end() - 1)

        # adding ':' at source.end()
        if (
            (restorative or pt >= source.end()) and
            (source_end_scope == ['source.python'] or
             source_end_scope == ['source.python', 'meta.statement.conditional.python'] or
             source_end_scope == ['source.python', 'comment.line.number-sign.python', 'punctuation.definition.comment.python'] or
             source_end_scope == ['source.python', 'meta.function.python']) and
            'meta.group.python' not in source_end_scope and
            source_end_prev_scope[-1] not in [
                'punctuation.section.arguments.begin.python',
                'punctuation.section.block.conditional.python',
                'punctuation.section.block.for.python',
                'punctuation.section.block.python',
                'punctuation.section.block.while.python',
                'punctuation.section.group.begin.python',
                'punctuation.section.mapping-or-set.begin.python',
                'punctuation.section.sequence.begin.python',
                'punctuation.separator.arguments.python',
                'punctuation.separator.continuation.line.python',
                'punctuation.separator.parameters.python',
                'punctuation.separator.sequence.python'
            ]
        ):
            add, where = False, -1

            if 'meta.statement.if.python' in source_end_prev_scope:
                if_source_begin, if_pt, inline_else_pt = python_if_analysis(view, edit, source.end() - 1)
                if if_source_begin == if_pt:
                    if report:
                        print("if_source_begin, if_pt, inline_else_pt:", if_source_begin, if_pt, inline_else_pt)
                    add, where = True, 0

            elif source_end_prev_scope[-1] in [
                'keyword.control.flow.conditional.python',
                'meta.statement.for.python',
                'meta.statement.while.python',
                'keyword.control.flow.try.python',
                'punctuation.section.inheritance.end.python'
            ]:
                add, where = True, 1

            elif (source_end_prev_scope == ['source.python', 'meta.statement.except.python', 'support.type.exception.python']):
                add, where = True, 2

            elif (len(source_end_prev_scope) > 1 and
                  source_end_prev_scope[1] in ['meta.statement.for.python', 'meta.statement.while.python']):
                add, where = True, 3

            elif 'meta.statement.conditional.python' in source_end_scope:
                add, where = True, 4

            elif (source_end_scope == ['source.python', 'meta.function.python'] and
                  source_end_prev_scope == ['source.python', 'meta.function.parameters.python', 'punctuation.section.parameters.end.python']):
                add, where = True, 5

            elif 'meta.statement.with.python' in source_end_prev_scope:
                add, where = True, 6

            if add:
                if report:
                    print(": being inserted AT source.end()", where)
                insert(':', source.end())

        # adding ':' at pt
        if (
            not restorative and
            len(pt_prev_scope) > 1 and
            (
                pt_prev_scope[1] in [
                    'meta.statement.if.python',
                    'meta.statement.conditional.python'
                ] or
                pt_prev_scope[-2:] == ['meta.function.parameters.python', 'punctuation.section.parameters.end.python']
            ) and
            'meta.group.python' not in pt_scope and
            'meta.sequence.list.python' not in pt_scope and
            'keyword.operator.arithmetic.python' not in pt_prev_scope and
            'keyword.operator.logical.python' not in pt_prev_scope and
            pt_prev_scope[-1] not in [
                'punctuation.section.arguments.begin.python',
                'punctuation.section.block.conditional.python',
                'punctuation.section.block.for.python',
                'punctuation.section.block.python',
                'punctuation.section.block.while.python',
                'punctuation.section.group.begin.python',
                'punctuation.section.mapping-or-set.begin.python',
                'punctuation.section.sequence.begin.python',
                'punctuation.separator.arguments.python',
                'punctuation.separator.continuation.line.python',
                'punctuation.separator.parameters.python',
                'punctuation.separator.sequence.python'
            ]
        ):
            if pt_prev_scope[1] == 'meta.statement.if.python':
                if_source_begin, if_pt, inline_else_pt = python_if_analysis(view, edit, pt_4_pt_prev_scope)
                if if_source_begin == if_pt:
                    left_trim_whitespace()
                    if report:
                        print(": being inserted at pt (case A)")
                    insert(':', pt)

                else:
                    left_trim_whitespace()
                    if inline_else_pt is None or \
                       inline_else_pt >= pt_4_pt_prev_scope - 3:
                        if report:
                            print("inline_else_pt, pt_4_pt_prev_scope:", inline_else_pt, pt_4_pt_prev_scope)
                        insert(' \\', pt)

            else:
                left_trim_whitespace()
                if report:
                    print(": being inserted at pt (case B)")
                insert(':', pt)

        else:
            pass
            # print("didn't insert ':' at pt with pt_scope:")
            # print(pt_scope)
            # print("pt_prev_scope:")
            # print(pt_prev_scope)

    if not restorative:
        left_trim_whitespace()
        right_trim_whitespace()

        if line.size() == 0 and line.begin() > 0:
            indent, zerg = python_indent_for_newline_at_pt(view, edit, line.begin() - 1)
            if zerg == 'b1' or zerg == 'c1':
                insert(' ' * indent + 'pass', line.begin())

            elif report:
                print("zerg:", zerg)

    if comment and (restorative or pt > comment.begin()):
        adjust_pre_comment_space()

    if not restorative and comment and comment.begin() < pt < line.end():
        old_pt = pt
        if view.substr(Region(pt, pt + 1)) != '#':
            insert('#', pt)
        move_pt_to(old_pt + 1)
        if pt < line.end() and view.substr(Region(pt, pt + 1)) != ' ':
            insert(' ', pt)
        move_pt_to(old_pt)

    if restorative:
        line_end_trim_whitespace()


def scope_as_array(view, pt):
    return view.scope_name(pt).split()


def show_scope(view, pt, message):
    showing_today = [
        # 'python_intervening_inline_else',
        # 'python_closest_closing_group_at_left',
        # 'python_closest_opening_group_at_left',
        # 'python_beginning_of_scope_attached_to_closing_group',
        # 'comb_view_for_scope',
        'unclassified'
    ]

    if view is None and pt is None:
        return message in showing_today

    if any(message.startswith(x) for x in showing_today):
        scope = view.extract_scope(pt)
        row, col = view.rowcol(pt)
        message += " (%d, line no %d, column %d):" % (pt, row + 1, col + 1)
        print(message)
        if scope.begin() == 0 and \
           scope.end() == view.size():
            print("(scope = full file)")
            print("                ?")

        else:
            string = view.substr(scope)
            pieces = string.split("\n")
            beginning_of_next_piece_pt = scope.begin()
            printed = False
            for p in pieces:
                print(p)
                if beginning_of_next_piece_pt <= pt <= beginning_of_next_piece_pt + len(p):
                    print(" " * (pt - beginning_of_next_piece_pt) + "^")
                    printed = True
                beginning_of_next_piece_pt = beginning_of_next_piece_pt + len(p) + 1
            assert printed
            line = view.line(pt)
            print("AND THE LINE:")
            print(view.substr(line))


def python_closest_closing_group_at_left(view, pt):
    if report:
        print("STARTING python_closest_closing_group_at_left")

    line, code, comment = python_line_regions_from_pt(view, pt)
    soft_bol_pt = code.begin() if code else line.end()

    if pt <= soft_bol_pt:
        if pt < soft_bol_pt:
            if report:
                print("warning: pt < soft_bol_pt in python_closest_closing_group_at_left (1a)")
    return pt, None

    pt = pt - 1
    while True:
        last = scope_as_array(view, pt)[-1]

        show_scope(view, pt, "python_closest_closing_group_at_left current scope")

        if last in python_closing_group_scopes:
            return pt, last

        elif last in python_atomic_scopes:
            extended = view.extract_scope(pt)
            if extended.begin() < pt:
                pt = extended.begin()
                if pt < soft_bol_pt:
                    if report:
                        print("warning: pt < soft_bol_pt in python_closest_closing_group_at_left (2s)")
                    return pt, None
                continue

        elif last in python_certified_nonatomic_scopes:
            pass

        elif report:
            show_scope(view, pt, "unclassified scope (atomic or non-atomic?):" + last)

        if pt == soft_bol_pt:
            if report:
                print("python_closest_closing_group_at_left breaking b/c reached soft_bol_pt")
            break

        pt -= 1

    assert pt == soft_bol_pt
    return pt, None


def python_beginning_of_scope_attached_to_closing_group(view, edit, pt):
    if report:
        print("STARTING python_beginning_of_scope_attached_to_closing_group")

    # This because of some bug in the ST scope generator:
    if pt == view.size():
        pt -= 1

    scope_name = scope_as_array(view, pt)[-1]
    if scope_name not in python_closing_group_scopes:
        l, source, c = python_line_regions_from_pt(view, pt)
        if report:
            print("offending scope_name:", scope_name)
            print("source, pt:", source, pt)
            print(view.substr(source))
        assert False

    original_pt = pt
    found = False

    while pt > 0:
        old_pt = pt
        sn1 = scope_as_array(view, pt)[-1]
        if sn1 in python_closing_group_scopes[scope_name]:
            found = True
            break
        view.insert(edit, pt, ' ')
        extended = view.extract_scope(pt)
        show_scope(view, pt, "python_beginning_of_scope_attached_to_closing_group extended")
        view.erase(edit, Region(pt, pt + 1))
        sn2 = scope_as_array(view, extended.begin())[-1]
        if sn2 in python_closing_group_scopes[scope_name]:
            found = True
            pt = extended.begin()
            break
        if extended.begin() == pt:  # (I've seen this happen with '    }' at the beginning of a line)
            pt = extended.begin() - 1
        else:
            assert pt > extended.begin()
            pt = extended.begin()
        assert old_pt > pt

    if not found:
        if report:
            print("~ warning: python_beginning_of_scope_attached_to_closing_group unable to find opening pt")
            print("~ scope_name:", scope_name)
            print("~ wanted to find one of:", python_closing_group_scopes[scope_name])
        assert False

    if found:
        assert pt < original_pt

    return pt


def python_closest_opening_group_at_left(view, edit, pt):
    def reset_soft_bol_pt():
        nonlocal pt, soft_bol_pt, line, source, comment
        if pt < soft_bol_pt:
            line, source, comment = python_line_regions_from_pt(view, pt)
            soft_bol_pt = source.begin() if source else line.end()
            if pt < soft_bol_pt:
                if report:
                    print("From package PythonSmartNewline (feel free to ignore):")
                    print("~ warning: pt < soft_bol_pt in python_closest_opening_group_at_left (2)")
                    if show_scope(None, None, "python_closest_opening_group_at_left"):
                        print("~ python_closest_opening_group_at_left returning False from within reset_soft_bol_pt")
                return False
        return True

    if report:
        print("STARTING python_closest_opening_group_at_left")

    show_scope(view, pt, "python_closest_opening_group_at_left very first scope")

    line, source, comment = python_line_regions_from_pt(view, pt)
    soft_bol_pt = source.begin() if source else line.end()

    if pt <= soft_bol_pt:
        if pt < soft_bol_pt:
            if report:
                print("warning: pt < soft_bol_pt in python_closest_opening_group_at_left (1)")

        if show_scope(None, None, "python_closest_opening_group_at_left"):
            if report:
                print("python_closest_opening_group_at_left returning None because pt <= soft_bol_pt")

        return pt, None

    pt = pt - 1

    if report:
        print("top of python_closest_opening_group_at_left, soft_bol_pt:", soft_bol_pt)

    while True:
        if report:
            if show_scope(None, None, "python_closest_opening_group_at_left"):
                print("\nTOP OF LOOP")

        extended = view.extract_scope(pt)
        if report:
            show_scope(view, pt, "python_closest_opening_group_at_left top of loop, extended (%d)" % pt)

        old_pt = pt
        pt_scope = scope_as_array(view, pt)

        if pt_scope[-1] in python_opening_group_scopes:
            if report and show_scope(None, None, "python_closest_opening_group_at_left"):
                print("python_closest_opening_group_at_left found an opening scope, returning")
            return pt, pt_scope[-1]

        elif (
            pt_scope[-1] == 'punctuation.definition.string.end.python' and
            (
                (  # not a block quote...
                    'string.quoted.double.block.python' not in pt_scope and
                    'string.quoted.single.block.python' not in pt_scope
                ) or
                (  # ...or else truly end of block quote
                    'punctuation.definition.string.end.python' in scope_as_array(view, pt - 1) and
                    'punctuation.definition.string.end.python' in scope_as_array(view, pt - 2)
                )
            )
        ):
            # truly at end of string; treat like being at closing scope; go to start of string
            if report and show_scope(None, None, "python_closest_opening_group_at_left"):
                print("python_closest_opening_group_at_left jumping to start of string")
            extended = view.extract_scope(pt)
            pt = extended.begin()
            if pt >= old_pt:
                # this can happen when two strings are side-by-side in the code (which is a
                # syntax error, actually)
                assert pt == old_pt
                extended = view.extract_scope(pt - 1)
                pt = extended.begin()
            assert pt < old_pt
            if not reset_soft_bol_pt():
                return pt, None
            continue

        elif pt_scope[-1] in [
            'string.quoted.double.block.python',
            'string.quoted.single.block.python'
        ]:
            extended = view.extract_scope(pt)

            if all('punctuation.definition.string.begin.python' in scope_as_array(view, extended.begin() + i) for i in [0, 1, 2]):
                row2, col2 = view.rowcol(extended.begin())
                row1, col1 = view.rowcol(pt)
                assert row2 <= row1
                if row2 == row1:
                    if report and show_scope(None, None, "python_closest_opening_group_at_left"):
                        print("python_closest_opening_group_at_left returning beginning of triple quote string + 2")
                    return extended.begin() + 2, 'punctuation.definition.string.begin.python'
                if report and show_scope(None, None, "python_closest_opening_group_at_left"):
                    print("python_closest_opening_group_at_left returning None pt B")
                return pt, None

            else:
                pt = extended.begin() - 1
                pt_scope = scope_as_array(view, pt)
                if 'string.quoted.double.block.python' not in pt_scope and \
                   'string.quoted.single.block.python' not in pt_scope:
                    assert 'punctuation.section.interpolation.end.python' in pt_scope
                    new_pt = python_beginning_of_scope_attached_to_closing_group(view, edit, pt)
                    if new_pt is None:
                        return None, None
                    assert new_pt < pt
                    pt = new_pt - 1
                    continue

        elif pt_scope[-1] in python_closing_group_scopes:
            if report and show_scope(None, None, "python_closest_opening_group_at_left"):
                print("found closing scope, going back to matching opening")
            pt = python_beginning_of_scope_attached_to_closing_group(view, edit, pt) - 1
            assert pt < old_pt
            if not reset_soft_bol_pt():
                return pt, None
            continue

        elif pt_scope[-1] in python_atomic_scopes:
            if report and show_scope(None, None, "python_closest_opening_group_at_left"):
                print("trying to use an atomic scope")
            extended = view.extract_scope(pt)
            if extended.begin() < pt:
                pt = extended.begin()
                assert pt < old_pt
                if not reset_soft_bol_pt():
                    return pt, None
                continue

        elif pt_scope[-1] == 'source.python':
            if report:
                print("python_closest_opening_group_at_left returning because swimming in source.python (?)")
            return pt, None

        elif pt_scope[-1] in python_certified_nonatomic_scopes:
            pass

        else:
            show_scope(view, pt, "python_closest_opening_group_at_left unclassified scope")

        if pt == soft_bol_pt:
            break

        pt -= 1
        if report and show_scope(None, None, "python_closest_opening_group_at_left"):
            print("decreased pt at end of main loop; pt is now", pt)

        assert 0 <= pt < old_pt

    assert pt == soft_bol_pt
    return pt, None


def python_scope_indent_for_pt_as_region(view, edit, pt, follow_line_continuations=False):
    if report:
        print("STARTING python_scope_indent_for_pt_as_region")
    z = pt
    while True:
        z, scope = python_closest_closing_group_at_left(view, z)
        if scope is not None:
            z = python_beginning_of_scope_attached_to_closing_group(view, edit, z)
            continue
        if not follow_line_continuations:
            break
        row, _ = view.rowcol(z)
        if row > 0:
            xline, xcode, xcomment = python_line_regions_from_line_no(view, row - 1)
            if xcode is not None and \
               scope_as_array(view, xcode.end() - 1)[-1] == 'punctuation.separator.continuation.line.python':
                assert xcode.end() < z
                z = xcode.end()
                continue
        break

    xline, xcode, xcomment = python_line_regions_from_pt(view, z)
    if xcode is not None:
        return Region(xline.begin(), xcode.begin())
    if xcomment is not None:
        return Region(xline.begin(), xcomment.begin())
    return Region(xline.begin(), xline.end())


def python_prev_line_ends_with_backslash(view, edit, pt):
    pt = semantic_bol(view, edit, pt)
    row, col = view.rowcol(pt)
    if row == 0:
        return False, None
    prev_line, prev_code, prev_comment = python_line_regions_from_line_no(view, row - 1)
    if not prev_code or \
       not scope_as_array(view, prev_code.end() - 1)[-1] == 'punctuation.separator.continuation.line.python':
        return False, None
    u = prev_code.end() - 1
    while u > prev_code.begin() and view.substr(Region(u, u - 1)) == ' ':
        u -= 1
    u = max(prev_code.begin(), u)
    return True, u


def python_indent_for_newline_at_pt(view, edit, pt):
    if report:
        print("STARTING python_indent_for_newline_at_pt")

    row, col = view.rowcol(pt)

    line, source, comment = python_line_regions_from_pt(view, pt)

    # take care of empty line problem
    if line.size() == 0:
        print("python_indent_for_newline_at_pt will go back to look for nonempty line")
        go_back = 1
        while go_back <= min(1, row):
            python_prepare_newline_at_pt(view, edit, view.text_point(row - go_back, 0), True)
            xline, xcode, xcomment = python_line_regions_from_line_no(view, row - go_back)

            if xline.size() > 0:
                print("recursive call to python_indent_for_newline_at_pt at go_back =", go_back)
                return python_indent_for_newline_at_pt(view, edit, xline.end())

            go_back += 1

        return 0, "fail 1"

    # take care of indent caused by in-line unclosed scope
    pt2, scope = python_closest_opening_group_at_left(view, edit, pt)

    if scope is not None:
        assert pt2 <= pt - 1
        if pt2 == pt - 1:
            indent = python_scope_indent_for_pt_as_region(view, edit, pt2)
            return indent.size() + 4, 'a1'

        if pt2 == pt - 4 and \
           'punctuation.definition.string.begin.python' in scope_as_array(view, pt - 3) and \
           'punctuation.definition.string.begin.python' in scope_as_array(view, pt - 2) and \
           'punctuation.definition.string.begin.python' in scope_as_array(view, pt - 1):
            indent = python_scope_indent_for_pt_as_region(view, edit, pt2)
            return indent.size() + 4, 'a1.5'

        if pt2 == pt - 5 and \
           'storage.type.string.python' in scope_as_array(view, pt - 4) and \
           'punctuation.definition.string.begin.python' in scope_as_array(view, pt - 3) and \
           'punctuation.definition.string.begin.python' in scope_as_array(view, pt - 2) and \
           'punctuation.definition.string.begin.python' in scope_as_array(view, pt - 1):
            indent = python_scope_indent_for_pt_as_region(view, edit, pt2)
            return indent.size() + 4, 'a1.6'

        row, col = view.rowcol(pt2)
        return col + 1, 'a2'

    assert scope is None

    we_end_with_backslash = False
    if col > 0:
        if scope_as_array(view, pt - 1)[-1] == 'punctuation.separator.continuation.line.python':
            we_end_with_backslash = True

    prev_ends_with_backslash, _ = python_prev_line_ends_with_backslash(view, edit, pt)

    # case 1 (recently changed, maybe first two cases should be merged, case 2 eliminated)
    if not we_end_with_backslash and not prev_ends_with_backslash:
        indent = python_scope_indent_for_pt_as_region(view, edit, pt, follow_line_continuations=True)
        indent_scope = scope_as_array(view, indent.end())
        pt_scope = scope_as_array(view, pt)

        if col > 0:
            prev_scope = scope_as_array(view, pt - 1)
            if prev_scope[-1] in python_colon_scopes:
                return indent.size() + 4, 'b1'

            if prev_scope[-1] in 'punctuation.section.class.begin.python' and \
               prev_scope[-2] in 'meta.class.python':
                return indent.size() + 4, 'b2'

        if indent_scope[-1] in [
            'keyword.control.flow.return.python',
            'keyword.control.flow.break.python',
            'keyword.control.flow.pass.python',
            'keyword.control.flow.continue.python',
            'keyword.control.flow.raise.python',
            'storage.type.class.python'
        ]:
            return indent.size() - 4, 'b3'

        if indent_scope[-1] == 'keyword.other.assert.python' and \
           view.substr(Region(indent.end(), pt)) == 'assert False':
            return indent.size() - 4, 'b4'

        return indent.size(), 'ordinary'

    # case 2
    if not we_end_with_backslash and \
       prev_ends_with_backslash:
        # print("case 2")
        indent = python_scope_indent_for_pt_as_region(view, edit, pt, follow_line_continuations=True)
        if col > 0 and scope_as_array(view, pt - 1)[-1] in python_colon_scopes:
            return indent.size() + 4, 'c1'
        indent_scope = scope_as_array(view, indent.end())
        if indent_scope[-1] == 'keyword.control.flow.return.python' or \
           indent_scope[-1] == 'keyword.control.flow.break.python':  # ?? (how could break occur within line continuation??)
            return indent.size() - 4, 'c2'
        return indent.size(), 'c3'  # this used to be indent.size() - 4 but couldn't remember why... (case where indent.size() is appropriate: pretty much anything?)

    # case 3
    if we_end_with_backslash and \
       not prev_ends_with_backslash:
        # print("case 3")
        indent = python_scope_indent_for_pt_as_region(view, edit, pt)
        pt_scope = scope_as_array(view, pt)
        if len(pt_scope) > 1 and pt_scope[1] == 'meta.statement.if.python':
            if_source_begin, if_pt, inline_else_pt = python_if_analysis(view, edit, pt)
            if if_source_begin == if_pt:
                return indent.size() + 3, 'd1'
        return indent.size() + 4, 'd2'

    # case 4
    if we_end_with_backslash and \
       prev_ends_with_backslash:
        # print("case 4")
        indent = python_scope_indent_for_pt_as_region(view, edit, pt)
        return indent.size(), 'e3'

    assert False


def generic_make_line_indent_no_more_than(view, edit, line_no, indent):
    line, source = generic_line_regions_from_line_no(view, line_no)
    if source:
        if source.begin() > indent + line.begin():
            view.erase(edit, Region(line.begin() + indent, source.begin()))

    else:
        if line.size() > indent:
            view.erase(edit, Region(line.begin() + indent, line.end()))


def python_check_line_for_closing_scope_that_should_be_moved_down(view, edit, pt):
    if report:
        print("WELCOME TO PYTHON_CHECK_LINE_FOR_CLOSING_SCOPE_THAT_SHOULD_BE_MOVED_DOWN")
    regions = view.sel()
    line, source, comment = python_line_regions_from_pt(view, pt)
    if not source:
        return

    assert source and pt == source.begin()

    pt_scope = scope_as_array(view, pt)

    if (
        pt_scope[-1] in python_closing_group_scopes or
        (
            'punctuation.definition.string.end.python' in pt_scope and
            (
                'string.quoted.double.block.python' in pt_scope or
                'string.quoted.single.block.python' in pt_scope
            ) and
            pt + 2 <= view.size() and
            'punctuation.definition.string.end.python' in scope_as_array(view, pt + 1) and
            'punctuation.definition.string.end.python' in scope_as_array(view, pt + 2)
        )
    ):
        print("u doing something here, pt:", pt)
        print("pt_scope:", pt_scope)
        print("substr at pt:", view.substr(Region(pt, pt + 1)))

        if pt_scope[-1] in python_closing_group_scopes:
            # closing scope
            z = python_beginning_of_scope_attached_to_closing_group(view, edit, pt)

        else:
            # case of block quote
            z = view.extract_scope(pt).begin() + 2

        zl, zs, zc = python_line_regions_from_pt(view, z)
        if z == zs.end() - 1:
            must_replace = regions.contains(Region(pt))
            print("made it to here; must_replace:", must_replace)
            view.insert(edit, pt, '\n')
            line, source, comment = python_line_regions_from_pt(view, pt)
            bol = pt + 1
            if must_replace:
                assert regions.contains(Region(bol))
                regions.subtract(Region(bol))
                regions.add(Region(pt))
            indent, _ = python_indent_for_newline_at_pt(view, edit, zs.end())
            view.insert(edit, bol, ' ' * (indent - 4))

            # we continue by checking if the current line shouldn't be destroyed, by any chance?
            pl, ps, pc = python_line_regions_from_pt(view, line.begin() - 1)
            if ps is not None:
                scope = scope_as_array(view, ps.end() - 1)
                if scope[-1] not in [
                    'punctuation.separator.sequence.python',
                    'punctuation.separator.arguments.python',
                    'keyword.operator.logical.python',
                    'keyword.operator.arithmetic.python',
                    'punctuation.definition.string.begin.python',
                    'punctuation.separator.set.python'
                ] and scope[-1] not in python_opening_group_scopes:
                    print("Decided to destroy line")
                    view.erase(edit, Region(line.begin(), line.end() + 1))
                    regions.subtract(Region(line.begin()))
                    regions.add(Region(line.begin() + indent - 4))

        else:
            print("compare z, zs.end():", z, zs.end())


def python_smart_newline_for_region_of_index(view, edit, where, restorative, index):
    regions = view.sel()

    assert 0 <= index < len(regions)
    assert regions[index].size() == 0

    if where == 'here' and \
       view.line(regions[index].a).begin() == regions[index].a:
        view.insert(edit, regions[index].a, '\n')
        index += 1
        return

    line, source, comment = python_line_regions_from_pt(view, regions[index].a)
    original_line_string = view.substr(line)
    python_prepare_newline_at_pt(view, edit, regions[index].a, restorative)

    if index >= len(regions):
        index = len(regions) - 1
        assert index >= 0

    if restorative:
        line_no, _ = view.rowcol(regions[index].a)
        new_bol = view.text_point(line_no + 1, 0)
        regions.subtract(regions[index])
        regions.add(Region(new_bol))
        indent, indent_type = python_indent_for_newline_at_pt(view, edit, new_bol - 1)
        generic_make_line_indent_no_more_than(view, edit, line_no + 1, indent)

    else:
        indent, indent_type = python_indent_for_newline_at_pt(view, edit, regions[index].a)
        if indent_type == "fail 1" and len(original_line_string) % 4 == 0 and all(x == ' ' for x in original_line_string):
            indent, indent_type = len(original_line_string), "fail 2"
        if report:
            print("indent_type:", indent_type)
        python_basic_newline_insert_at_pt(view, edit, regions[index].a)
        view.insert(edit, regions[index].a, " " * indent)
        python_check_line_for_closing_scope_that_should_be_moved_down(view, edit, regions[index].a)


def python_smart_newline(view, edit, where, restorative=False):
    def right_trim_whitespace(pt):
        if not is_inside_string_or_comment(view, pt):
            w = pt
            while view.substr(Region(w, w + 1)) == ' ':
                w += 1
            if w > pt:
                view.erase(edit, Region(pt, w))

    if report:
        print("")
        print("================================================")
        print("WELCOME TO PYTHON SMART NEWLINE; where =", where)

    regions = view.sel()

    # erase regions, or else replace them by single caret
    if where == 'here':
        for r in regions:
            view.erase(edit, r)

    else:
        bs = [r.b for r in regions]
        regions.clear()
        regions.add_all([Region(pt) for pt in bs])

    if where == 'eol':
        move_to_eol(view)

    assert all(r.size() == 0 for r in regions)

    index = 0
    while index < len(regions):
        python_smart_newline_for_region_of_index(view, edit, where, restorative, index)
        index += 1


def semantic_bol(view, edit, pt):
    def reset_basics(assert_source=True):
        nonlocal line, source, comment
        line, source, comment = python_line_regions_from_pt(view, u)
        if assert_source:
            assert source is not None
            assert source.begin() <= u

    u = pt
    line = None
    source = None
    comment = None
    reset_basics(assert_source=False)
    if source is None:
        assert comment is not None
        return comment.begin()

    while u > source.begin():
        u_scope = scope_as_array(view, u)

        must_reset_basics = False

        if u_scope[-1] in python_closing_group_scopes:
            next_u = python_beginning_of_scope_attached_to_closing_group(view, edit, u)
            if next_u is None:
                return source.begin()
            must_reset_basics = True

        elif u_scope[-1] in python_atomic_scopes:
            next_u = view.extract_scope(u).begin()
            must_reset_basics = True

        else:
            next_u = u

        u = min(u - 1, next_u)
        if must_reset_basics:
            reset_basics()

    return source.begin()


def get_cur_function_call_name(view, edit, pt):
    def reset_basics():
        nonlocal line, source, comment
        line, source, comment = python_line_regions_from_pt(view, u)
        assert source is not None

    line = None
    source = None
    comment = None

    u = pt
    reset_basics()

    next_u = u
    assert next_u > source.begin()
    u = next_u + 1

    while next_u > source.begin():
        assert next_u < u
        u = next_u

        u_scope = scope_as_array(view, u)

        # are we sitting on closing quote?
        if 'punctuation.definition.string.end.python' in u_scope:
            next_u = view.extract_scope(u).begin()
            assert next_u < u
            continue

        # skip past space
        while u > 0 and view.substr(Region(u - 1, u)) == ' ':
            u -= 1
        if u < next_u:
            assert u > source.begin()
            u_scope = scope_as_array(view, u)

        # read scope
        u_scope = scope_as_array(view, u)
        assert 'meta.function-call.arguments.python' in u_scope

        if 'punctuation.section.arguments.begin.python' in u_scope:
            extended = view.extract_scope(u - 1)
            return view.substr(extended)[:-1]

        # if 'string' in u_scope[-1] and \
        #    'punctuation.definition.string.begin.python' not in u_scope:
        #     print("u:", u)
        #     print("u_scope:", u_scope)

        assert \
            'string' not in u_scope[-1] or \
            'punctuation.definition.string.begin.python' in u_scope

        if u_scope[-1] in python_closing_group_scopes:
            next_u = python_beginning_of_scope_attached_to_closing_group(view, edit, u)
            if next_u is None:
                return None
            assert next_u < u
            continue

        elif u_scope[-1] in python_atomic_scopes:
            next_u = view.extract_scope(u).begin()

        if next_u >= u:
            print("end of loop reducing u:", u)
            next_u = u - 1

    return get_cur_function_call_name(view, edit, line.begin() - 1)


def retrieve_last_token(view, edit, pt):
    def reset_basics():
        nonlocal line, source, comment
        line, source, comment = python_line_regions_from_pt(view, u)
        assert source is not None

    line = None
    source = None
    comment = None

    u = pt
    while u > 0 and view.substr(Region(u - 1, u)) == ' ':
        u -= 1
    end = u

    reset_basics()

    u -= 1
    while u > source.begin():
        u_scope = scope_as_array(view, u)
        print("top of loop, u, u_scope[-1]:", u, u_scope[-1], view.substr(Region(u, u + 1)))

        if 'punctuation.definition.string.end.python' in u_scope:
            next_u = view.extract_scope(u).begin()
            assert next_u < u
            u = next_u
            reset_basics()
            break

        assert 'string' not in u_scope[-1] or \
            'punctuation.definition.string.begin.python' in u_scope or \
            (u_scope[-1] == 'storage.type.string.python' and view.substr(Region(u, u + 1)) in 'rf')

        if view.substr(Region(u - 1, u)) == ' ':
            break

        if any(x in u_scope[-1] for x in python_opening_group_scopes) or \
           any(x in u_scope[-1] for x in python_comma_scopes) or  \
           'keyword.operator.assignment.python' in u_scope:
            u += 1
            break

        must_reset_basics = False

        if u_scope[-1] in python_closing_group_scopes:
            next_u = python_beginning_of_scope_attached_to_closing_group(view, edit, u)
            if next_u is None:
                return None
            must_reset_basics = True

        elif u_scope[-1] in python_atomic_scopes:
            next_u = view.extract_scope(u).begin()
            must_reset_basics = True

        else:
            next_u = u

        u = min(u - 1, next_u)
        if must_reset_basics:
            reset_basics()

    return Region(u, end)


def is_post_first_token(view, edit, pt):
    def reset_basics():
        nonlocal line, source, comment
        line, source, comment = python_line_regions_from_pt(view, u)
        assert source is not None

    u = pt
    line = None
    source = None
    comment = None
    reset_basics()

    prev_ends_with_backslash, where = python_prev_line_ends_with_backslash(view, edit, pt)
    if prev_ends_with_backslash:
        return False

    while u > source.begin():
        u_scope = scope_as_array(view, u)

        # assert not any('string' in x for x in u_scope) or \
        #     'punctuation.definition.string.begin.python' in u_scope or \
        #     'punctuation.definition.string.end.python' in u_scope

        if view.substr(Region(u, u - 1)) == ' ':
            if any('string' in x for x in u_scope) and \
               'punctuation.definition.string.begin.python' not in u_scope and \
               'punctuation.definition.string.end.python' not in u_scope and \
               (u_scope[-1] != 'storage.type.string.python' or view.substr(Region(u, u + 1)) not in 'rf'):
                print("ur about to crash with u:", u)
            assert not any('string' in x for x in u_scope) or \
                'punctuation.definition.string.begin.python' in u_scope or \
                'punctuation.definition.string.end.python' in u_scope or \
                (u_scope[-1] == 'storage.type.string.python' and view.substr(Region(u, u + 1)) in 'rf')
            u -= 1
            assert u > source.begin()
            while view.substr(Region(u, u - 1)) == ' ':
                u -= 1
                assert u > source.begin()
            if view.substr(Region(u, u - 1)) != ',':
                # print("returning False pt A; u:", u)
                return False
            u -= 1
            continue

        if 'keyword.operator.assignment.python' in u_scope:
            # print("returning False pt B")
            return False

        must_reset_basics = False

        if u_scope[-1] in python_closing_group_scopes:
            print("u be using 1:", u_scope[-1])
            next_u = python_beginning_of_scope_attached_to_closing_group(view, edit, u)
            if next_u is None:
                # print("returning False pt C")
                return False
            must_reset_basics = True

        elif u_scope[-1] in python_atomic_scopes:
            print("u be using 2:", u_scope[-1])
            next_u = view.extract_scope(u).begin()
            must_reset_basics = True

        else:
            print("u be using 3:", u_scope[-1])
            next_u = u

        u = min(u - 1, next_u)
        if must_reset_basics:
            reset_basics()

    print("returning True very end!")
    return True


def is_post_assignment(view, pt):
    line, source, comment = python_line_regions_from_pt(view, pt)
    assert source is not None

    u = pt
    while u > source.begin() and view.substr(Region(u, u - 1)) == ' ':
        u -= 1
    u -= 1

    u_scope = scope_as_array(view, u)

    return \
        'keyword.operator.assignment.python' in u_scope or \
        'keyword.operator.assignment.augmented.python' in u_scope


def is_post_token_that_is_post_assignment(view, edit, pt):
    token_region = retrieve_last_token(view, edit, pt)
    return \
        token_region is not None and is_post_assignment(view, token_region.begin())


def is_post_operator(view, pt):
    line, source, comment = python_line_regions_from_pt(view, pt)

    assert source is not None
    assert source.begin() <= pt

    u = pt
    while view.substr(Region(u, u - 1)) == ' ':
        u -= 1
        assert u > source.begin()

    u -= 1
    u_scope = scope_as_array(view, u)

    if u_scope[-1] == 'keyword.operator.comparison.python':
        return True

    if u_scope[-1] == 'keyword.operator.arithmetic.python':
        return True

    if u_scope[-1] == 'keyword.operator.logical.python':
        return True

    return False


def is_post_mantissa(view, edit, pt):
    if view.substr(Region(pt - 1, pt)) != 'e':
        return False

    view.insert(edit, pt, '10')
    pt_scope = scope_as_array(view, pt)
    view.erase(edit, Region(pt, pt + 2))
    return pt_scope[-1] == 'constant.numeric.float.python'


def is_at_soft_bol_or_at_beginning_of_list_etc(view, pt):
    line, source, comment = python_line_regions_from_pt(view, pt)
    assert source is not None

    if pt <= source.begin():
        return True, 'no space no deletion'

    u = pt
    while view.substr(Region(u, u - 1)) == ' ':
        u -= 1
        assert u > line.begin()

    u -= 1
    u_scope = scope_as_array(view, u)

    if u_scope[-1] == 'invalid.illegal.empty-expression.python' and \
       'meta.string.interpolated.python' in u_scope and \
       view.substr(Region(u, u + 1)) == '{':
        return True, 'no space'

    if u_scope[-1] in [
        'punctuation.separator.arguments.python',
        'punctuation.separator.parameters.python',
        'punctuation.separator.sequence.python',
        'punctuation.separator.set.python',
        'punctuation.separator.tuple.python',
        'punctuation.separator.mapping.python',
        'punctuation.separator.mapping.key-value.python',
        'keyword.control.flow.return.python'
    ]:
        return True, 'space'

    if u_scope[-1] in [
        'punctuation.section.arguments.begin.python',
        'punctuation.section.brackets.begin.python',
        'punctuation.section.mapping.begin.python',
        'punctuation.section.parameters.begin.python',
        'punctuation.section.sequence.begin.python',
        'punctuation.section.set.begin.python',
        'punctuation.separator.slice.python'
    ]:
        return True, 'no space'

    if u_scope == ['source.python'] and \
       view.substr(Region(u, u + 1)) == ',':
        return True, 'space'

    return False, ''


def is_post_import(view, pt):
    u = pt
    while view.substr(Region(u, u - 1)) == ' ':
        u -= 1
    return 'keyword.control.import.python' in scope_as_array(view, u - 1)


def is_post_inline_else(view, pt):
    u = pt
    while view.substr(Region(u, u - 1)) == ' ':
        u -= 1
    return 'keyword.control.flow.else.inline.python' in scope_as_array(view, u - 1)


def operator_string_to_left(view, pt):
    line = view.line(pt)
    u = pt
    while u > line.begin() and view.substr(Region(u, u - 1)) in operator_chars:
        u -= 1
    return view.substr(Region(u, pt))


def operator_string_to_right(view, pt):
    line = view.line(pt)
    u = pt
    while u < line.end() and view.substr(Region(u, u + 1)) in operator_chars:
        u += 1
    return view.substr(Region(pt, u))


def move_left_past(view, pt, chars):
    line = view.line(pt)
    u = pt
    while u > line.begin() and view.substr(Region(u, u - 1)) in chars:
        u -= 1
    print("move_left_past pt, u:", pt, u)
    return u


def move_right_past(view, pt, chars):
    line = view.line(pt)
    u = pt
    while u > line.begin() and view.substr(Region(u, u - 1)) in chars:
        u -= 1
    return u


operator_chars = '=!-+*/%<> '
operator_chars_no_equals = '!-+*/%<> '
operator_chars_no_space = '=!-+*/%<>'


def first_try_classifier_4_operator_insertion(view, edit, pt):
    pt_scope = scope_as_array(view, pt)

    if is_inside_string_or_comment(view, pt, pt_scope):
        return 'string or block comment'

    line, source, comment = python_line_regions_from_pt(view, pt)

    if comment is not None and pt >= comment.begin() or \
       'comment.block.documentation.python' in pt_scope:
        return 'comment'

    if not source:
        return 'unknown'

    # game plan
    # - new expression
    # - post mantissa  # (not implemented yet)
    # - closest of:
    #   - group scope of any kind
    #   - function call scope
    # - function def scope
    # - post assignment keyword @pt
    # - post first token @left-of-operator-chars
    # - post token that is post assignment
    # - post operator
    # - post import

    at_beginning, space = is_at_soft_bol_or_at_beginning_of_list_etc(view, pt)
    if at_beginning:
        return 'new expression ' + space

    if is_post_mantissa(view, edit, pt):
        return 'post mantissa'

    if 'meta.function.parameters.python' in pt_scope or \
       'meta.function-call.arguments.python' in pt_scope:
        pt_4_pt_prev_scope = pt - 1
        while (
            pt_4_pt_prev_scope > source.begin() and
            view.substr(Region(pt_4_pt_prev_scope, pt_4_pt_prev_scope + 1)) == ' '
        ):
            pt_4_pt_prev_scope -= 1

        if view.substr(Region(pt_4_pt_prev_scope, pt_4_pt_prev_scope + 1)) == '=':
            pt_prev_scope = scope_as_array(view, pt_4_pt_prev_scope)
            if pt_prev_scope[-1] == 'keyword.operator.assignment.python' and \
               pt_prev_scope[-2] in ['meta.function-call.arguments.python',
                                     'meta.function.parameters.default-value.python']:
                return 'post assignment in args'

    group_last_index_1 = last_index_among_not_followed_by(pt_scope, [
        ['meta.group.python', 'punctuation.section.group.begin.python'],
        ['meta.set.python', 'punctuation.section.set.begin.python'],
        ['meta.mapping.python', 'punctuation.section.mapping.begin.python'],
        ['meta.sequence.list.python', 'punctuation.section.sequence.begin.python'],
        ['meta.sequence.tuple.empty.python', 'punctuation.section.sequence.begin.python'],
        ['meta.item-access.python', ('punctuation.section.brackets.begin.python', 'meta.qualified-name.python')],
        ['meta.sequence.tuple.python', 'punctuation.section.sequence.begin.python'],
        ['meta.interpolation.python', 'punctuation.section.interpolation.begin.python']
    ])

    group_last_index_2 = last_index_among(pt_scope, [
        'punctuation.section.mapping.end.python',
        'punctuation.section.sequence.end.python',
        'punctuation.section.brackets.end.python',
        'punctuation.section.group.end.python',
        'punctuation.section.interpolation.end.python',
        'meta.item-access.arguments.python'
    ])

    group_last_index = max(group_last_index_1, group_last_index_2)

    function_call_last_index = last_index_among_not_followed_by(pt_scope, [
        ['meta.function-call.arguments.python', 'punctuation.section.arguments.begin.python']
    ])

    if group_last_index > function_call_last_index:
        print("here's pt_scope that yielded group:", group_last_index_1, group_last_index_2)
        print(pt_scope)
        return 'group'

    if function_call_last_index > -1:
        prev_token_region = retrieve_last_token(view, edit, pt)
        if prev_token_region is not None:
            prev_token_str = view.substr(prev_token_region)
            if any(x in prev_token_str for x in '(.['):
                return 'function call post complex token'
        if get_cur_function_call_name(view, edit, pt) in [
            'any',
            'all'
        ]:
            return 'function call any all'
        return 'function call'

    if 'meta.function.parameters.python' in pt_scope:
        return 'function def'

    # post-assignment?
    if is_post_assignment(view, pt):
        return 'post assignment'

    # post operator?
    if is_post_operator(view, pt):
        return 'post operator'

    # post-first-token?
    if 'meta.statement.if.python' not in pt_scope and \
       'meta.statement.conditional.python' not in pt_scope and \
       is_post_first_token(view, edit, move_left_past(view, pt, operator_chars)):
        return 'post first token'

    # post-token-that-is-post-assignment?
    if is_post_token_that_is_post_assignment(view, edit, pt):
        return 'post token that is post assignment'

    # post import?
    if is_post_import(view, pt):
        return 'post import'

    # post else?
    if is_post_inline_else(view, pt):
        return 'new expression space'

    return 'unknown'


def python_quote_insert(view, edit, which):
    assert which in ['"', "'"]

    regions = view.sel()

    for r in regions:
        if r.size() > 0:
            view.insert(edit, r.end(), which)
            view.insert(edit, r.begin(), which)
            continue

        pt = r.a
        pt_scope = scope_as_array(view, pt)

        if not is_inside_string_or_comment(view, pt, pt_scope):
            view.insert(edit, pt, which * 2)
            regions.subtract(Region(pt + 2))
            regions.add(Region(pt + 1))
            continue

        liz = 'single' if which == "'" else 'double'

        if pt_scope[-2:] == ['string.quoted.%s.python' % liz, 'punctuation.definition.string.end.python']:
            prev_pt_scope = scope_as_array(view, pt - 1)
            if prev_pt_scope[-2:] == [
                'string.quoted.%s.python' % liz,
                'punctuation.definition.string.begin.python'
            ]:
                view.insert(edit, pt, which * 4)
            regions.subtract(Region(pt + 4))
            regions.add(Region(pt + 2))
            continue

        view.insert(edit, pt, which)


def python_smart_binary_operator(view, edit, symbol):
    def reset_basics():
        nonlocal line, source, comment
        line, source, comment = python_line_regions_from_pt(view, pt)

    def erase(r):
        nonlocal pt
        view.erase(edit, r)
        if r.begin() < pt < r.end():
            pt = r.begin()
            regions.add(Region(pt))
        elif pt >= r.end():
            pt -= r.size()
        reset_basics()

    def insert(string):
        nonlocal pt
        view.insert(edit, pt, string)
        pt += len(string)
        reset_basics()

    def trim_chars_left(chars):
        w = pt
        while w > line.begin() and view.substr(Region(w - 1, w)) in chars:
            w -= 1
        to_return = view.substr(Region(w, pt))
        erase(Region(w, pt))
        return to_return

    def trim_chars_right(chars):
        u = pt
        while u < line.end() and view.substr(Region(u, u + 1)) in chars:
            u += 1
        to_return = view.substr(Region(pt, u))
        erase(Region(pt, u))
        return to_return

    def trim_chars_left_right(chars):
        w = pt
        while w > line.begin() and view.substr(Region(w - 1, w)) in chars:
            w -= 1
        u = pt
        while u < line.end() and view.substr(Region(u, u + 1)) in chars:
            u += 1
        if w < u:
            to_return = view.substr(Region(w, u))
            erase(Region(w, u))
        else:
            to_return = ''
        return to_return

    line, source, comment = None, None, None
    regions = view.sel()

    for r in regions:
        if r.size() > 0:
            view.erase(edit, r)

    for r in regions:
        pt = r.a
        reset_basics()

        pt_class = first_try_classifier_4_operator_insertion(view, edit, pt)

        print("pt_class:", pt_class)

        assert pt_class in [
            'string or block comment',
            'comment',
            'unknown',
            'group',
            'function call',
            'function call any all',
            'function call post complex token',
            'function def',
            'post assignment',
            'post assignment in args',
            'post first token',
            'post token that is post assignment',
            'post import',
            'post mantissa',
            'post operator',
            'new expression space',
            'new expression no space',
            'new expression no space no deletion'
        ]

        chars2trimleft = operator_chars
        chars2trimright = operator_chars

        if pt_class in ['string or block comment', 'comment']:
            insert(symbol)
            continue

        if symbol in '+-' and pt_class.startswith('post assignment'):
            chars2trimleft = ' '

        elif symbol in '+-' and pt_class == 'post operator':
            chars2trimleft = ' '

        elif 'no deletion' in pt_class:
            chars2trimleft = ''

        existing_left = trim_chars_left(chars2trimleft)
        existing_right = trim_chars_right(chars2trimright)
        existing = existing_left + existing_right
        # existing = trim_chars_left_right(chars2trim)

        if symbol == '=':
            if pt_class == 'function def':
                insert('=')

            elif 'function call' in pt_class:
                if '<=' in existing or '>=' in existing:
                    insert(' == ')

                elif '<' in existing:
                    insert(' <= ')

                elif '>' in existing:
                    insert(' >= ')

                elif '!' in existing:
                    insert(' != ')

                elif ('post complex token' in pt_class or
                      'any all' in pt_class or
                      '==' in existing or
                      ' ' in existing):
                    insert(' == ')

                else:
                    insert('=')

            elif pt_class == 'group':
                if '<' in existing:
                    insert(' <= ')

                elif '>' in existing:
                    insert(' >= ')

                elif '!' in existing:
                    insert(' != ')

                else:
                    insert(' == ')

            elif (pt_class == 'post first token' or
                  pt_class == 'post token that is post assignment'):
                augmented_assignment_chars = '*+-/'

                if any(x in existing for x in augmented_assignment_chars):
                    for z in augmented_assignment_chars:
                        if z in existing:
                            insert(' ' + z + '= ')
                            break

                else:
                    if all(c == ' ' for c in existing) and existing_left != '':
                        insert(existing_left + '= ')

                    else:
                        insert(' = ')

            else:
                # exactly the same as 'group':
                if '<' in existing:
                    insert(' <= ')

                elif '>' in existing:
                    insert(' >= ')

                elif '!' in existing:
                    if '=' in existing:
                        insert(' == ')

                    else:
                        insert(' != ')

                else:
                    insert(' == ')

        elif symbol in '<>':
            if '=' in existing:
                insert(' ' + symbol + '= ')

            else:
                insert(' ' + symbol + ' ')

        elif symbol in '+-':
            if pt_class.startswith('new expression'):
                if 'no space' in pt_class:
                    insert(symbol)

                else:
                    insert(' ' + symbol)

            elif pt_class == 'post mantissa':
                insert(symbol)

            elif pt_class == 'post assignment in args':
                insert(symbol)

            elif (pt_class == 'post assignment' or
                  pt_class == 'post operator'):
                insert(' ' + symbol)

            elif pt_class == 'post first token':
                insert(' ' + symbol + '= ')

            else:
                insert(' ' + symbol + ' ')

        elif symbol == '*':
            if pt_class.startswith('new expression'):
                if 'no space' in pt_class:
                    insert('*')

                else:
                    insert(' *')

            elif pt_class in ['function def', 'function call']:
                if '*' in existing_left:
                    insert(' **')

                else:
                    insert(' *')

            elif pt_class == 'post first token':
                insert(' *= ')

            elif pt_class == 'post import':
                insert(' *')

            else:
                insert(' * ')

        elif symbol in '/':
            if pt_class == 'post first token':
                insert(' ' + symbol + '= ')

            elif '/' in existing:
                insert(' // ')

            else:
                insert(' ' + symbol + ' ')

        elif symbol in '%':
            if pt_class == 'post first token':
                insert(' ' + symbol + '= ')

            else:
                insert(' ' + symbol + ' ')

        elif symbol == '!':
            insert(' ' + symbol + '= ')

        else:
            insert(' ' + symbol + ' ')


def python_smart_binary_operator_backup(view, edit, symbol):
    regions = view.sel()

    for r in regions:
        if r.size() > 0:
            view.erase(edit, r)

    for r in regions:
        view.insert(edit, r.a, symbol)


def last_comment_indent_if_last_is_comment(view, pt):
    row, col = view.rowcol(pt)
    line_no = row - 1
    while line_no >= row - 2:
        line, source, comment = python_line_regions_from_line_no(view, line_no)
        if source is not None:
            return None

        if comment is not None:
            return comment.begin() - line.begin()

        line_no -= 1
    return None


def python_toggle_comment(view, edit):
    regions = view.sel()

    for r in regions:
        pt = r.b
        line, source, comment = python_line_regions_from_pt(view, pt)

        if source is None and comment is not None:
            u = comment.begin()
            view.erase(edit, Region(u, u + 1))
            if view.substr(Region(u, u + 1)) == ' ':
                view.erase(edit, Region(u, u + 1))

        elif source is not None:
            indent = last_comment_indent_if_last_is_comment(view, pt)
            if indent is not None and indent <= source.begin() - line.begin():
                view.insert(edit, line.begin() + indent, '# ')

            else:
                view.insert(edit, source.begin(), '# ')


def python_backslash(view, edit):
    regions = view.sel()

    for r in regions:
        if r.size() > 0:
            view.erase(edit, r)

    for index, r in enumerate(regions):
        pt = r.b
        view.insert(edit, pt, '\\')
        pt_scope = scope_as_array(view, pt)

        if pt_scope[-1] == 'punctuation.separator.continuation.line.python':
            python_smart_newline_for_region_of_index(view, edit, 'here', False, index)

        else:
            print("didn't do it cuz pt_scope:", pt_scope)


def python_forward_toggle_comment(view, edit):
    python_toggle_comment(view, edit)
    view.run_command("move", {"by": "lines", "forward": True})


def python_backward_toggle_comment(view, edit):
    view.run_command("move", {"by": "lines", "forward": False})
    python_toggle_comment(view, edit)


def pt_is_at_import_or_blank_line(view, pt):
    line, source, comment = python_line_regions_from_pt(view, pt)
    if source is None:
        return True
    row, col = view.rowcol(pt)
    bol = view.text_point(row, 0)
    if source.begin() > bol:
        return False
    bol_scope = scope_as_array(view, bol)
    return 'meta.statement.import.python' in bol_scope


def line_of_number_is_import_or_blank_line(view, line_no):
    bol = view.text_point(line_no, 0)
    line, source, comment = python_line_regions_from_pt(view, bol)
    return \
        source is None or \
        (source.begin() == bol and 'meta.statement.import.python' in scope_as_array(view, bol))


def this_and_all_previous_lines_are_import_or_blank_lines(view, line_no):
    i = line_no
    while i >= 0:
        if not line_of_number_is_import_or_blank_line(view, i):
            return False
        i -= 1
    return True


def appropriate_point_to_insert_from_keyword(view, pt):
    row, col = view.rowcol(pt)
    bol = view.text_point(row, 0)
    if bol < pt:
        return False
    return this_and_all_previous_lines_are_import_or_blank_lines(view, row)


def appropriate_point_to_insert_bol_import_keyword(view, pt):
    row, col = view.rowcol(pt)
    if not this_and_all_previous_lines_are_import_or_blank_lines(view, row):
        return False
    line, source, comment = python_line_regions_from_pt(view, pt)
    return source is None and pt == line.begin()


def appropriate_point_to_insert_from_import_keyword(view, pt):
    line, source, comment = python_line_regions_from_pt(view, pt)
    if source is None or pt <= source.begin():
        return False
    if 'keyword.control.import.from.python' not in scope_as_array(view, source.begin()):
        return False
    substring = view.substr(Region(source.begin(), pt))
    assert substring.startswith('from')
    return \
        substring[-1] == ' ' and \
        len(substring.split()) == 2


def appropriate_point_to_insert_import_keyword(view, pt):
    return \
        appropriate_point_to_insert_bol_import_keyword(view, pt) or \
        appropriate_point_to_insert_from_import_keyword(view, pt)


class PythonSmartNewlineCommand(sublime_plugin.TextCommand):
    def run(self, edit, where, restorative=False):
        python_smart_newline(self.view, edit, where, restorative)


class PythonSmartBinaryOperatorCommand(sublime_plugin.TextCommand):
    def run(self, edit, which):
        python_smart_binary_operator(self.view, edit, which)


class PythonQuoteInsertCommand(sublime_plugin.TextCommand):
    def run(self, edit, which):
        python_quote_insert(self.view, edit, which)


class PythonBackslashCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        python_backslash(self.view, edit)


class PythonForwardToggleCommentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        print("you are in PythonForwardToggleCommentCommand")
        python_forward_toggle_comment(self.view, edit)


class PythonBackwardToggleCommentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        python_backward_toggle_comment(self.view, edit)


class ClosePanelAndForwardToggleCommentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        python_forward_toggle_comment(file_view, edit)


class ClosePanelAndBackwardToggleCommentCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        python_backward_toggle_comment(file_view, edit)


def python_delete_underlying_true_false(view, edit, r):
    string = view.substr(r)
    if string not in 'True' and string not in 'False':
        return False

    a = r.begin()
    b = r.end()

    while view.substr(Region(a, a - 1)) in 'TrueFalse' and a >= b - 5:
        a -= 1

    while view.substr(Region(b, b + 1)) in 'TrueFalse' and b <= a + 5:
        b += 1

    if view.substr(Region(a, b)) not in ['True', 'False'] or \
       scope_as_array(view, a)[-1] != 'constant.language.python':
        return

    view.erase(edit, Region(a, b))


def delete_underlying_true_false_and_insert(view, edit, val):
    assert val in ['True', 'False']

    regions = view.sel()

    for r in regions:
        python_delete_underlying_true_false(view, edit, r)

    for r in regions:
        if r.size() > 0:
            continue

        view.insert(edit, r.begin(), val)


class PythonInsertTrueCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        delete_underlying_true_false_and_insert(self.view, edit, 'True')


class PythonInsertFalseCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        delete_underlying_true_false_and_insert(self.view, edit, 'False')


def python_region_true_false_replaceable(view, r):
    end_scope = scope_as_array(view, r.end())
    begin_scope = scope_as_array(view, r.begin())

    def is_inside_true_false_keyword():
        if end_scope[-1] != 'constant.language.python' or \
           begin_scope[-1] != 'constant.language.python' or \
           r.size() > 5:
            return False

        string = view.substr(r)
        if string not in 'True' and string not in 'False':
            return False

        a = r.begin()
        b = r.end()

        while view.substr(Region(a, a - 1)) in 'TrueFalse' and a >= b - 5:
            a -= 1

        while view.substr(Region(b, b + 1)) in 'TrueFalse' and b <= a + 5:
            b += 1

        return view.substr(Region(a, b)) in ['True', 'False']

    def is_right_after_true_false_keyword():
        if r.size() > 0:
            return False

        pt = r.end()
        pt_prev_scope = scope_as_array(view, pt - 1)

        if pt_prev_scope[-1] not in 'constant.language.python':
            return False

        a = r.begin()
        b = r.end()

        while view.substr(Region(a, a - 1)) in 'TrueFalse' and a >= b - 5:
            a -= 1

        while view.substr(Region(b, b + 1)) in 'TrueFalse' and b <= a + 5:
            b += 1

        return view.substr(Region(a, b)) in ['True', 'False']

    def true_false_somehow_expected():
        if r.size() > 0:
            return False

        # (here too, haha)
        pt = r.end()

        if pt < view.size():
            next_char = view.substr(Region(pt, pt + 1))

        else:
            next_char = '\n'

        if next_char not in ' \n)}],':
            return False

        line, source, comment = python_line_regions_from_pt(view, pt)

        if source is None:
            return False

        pt_prev_scope = scope_as_array(view, pt - 1)

        if pt_prev_scope[-1] == 'keyword.operator.assignment.python' and \
           pt_prev_scope[-2] in ['meta.function-call.arguments.python', 'meta.function.parameters.default-value.python'] and \
           next_char in ',)':
            return True

        if pt > 0:
            prev_char = view.substr(Region(pt - 1, pt))

        else:
            prev_char = '\n'

        pt_prev_prev_scope = scope_as_array(view, pt - 2)

        if prev_char == ' ' and \
           pt_prev_prev_scope[-1] in [
               'keyword.control.flow.return.python',
               'keyword.operator.logical.python',
               'keyword.operator.assignment.python',
               'keyword.other.assert.python'
           ]:
            return True

        if prev_char == ' ' and \
           pt_prev_prev_scope[-1] in 'keyword.control.flow.conditional.python' and \
           view.substr(Region(pt - 3, pt - 1)) == 'if':
            return True

        pt_scope = scope_as_array(view, pt)

        if 'meta.mapping.python' in pt_scope and \
           'punctuation.separator.mapping.key-value.python' not in pt_scope:
            u = pt - 1
            while u > source.begin() and view.substr(Region(u, u + 1)) == ' ':
                u -= 1
            u_scope = scope_as_array(view, u)
            if 'punctuation.separator.mapping.key-value.python' in u_scope:
                return True

        return False

    return \
        is_inside_true_false_keyword() or \
        is_right_after_true_false_keyword() or \
        true_false_somehow_expected()


def python_all_selections_true_false_replaceable(view):
    regions = view.sel()
    return all(python_region_true_false_replaceable(view, r) for r in regions)


class PythonAllSelectionsTrueFalseReplaceable(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match):
        if key != 'python_all_selections_true_false_replaceable':
            return None

        result = python_all_selections_true_false_replaceable(view)

        if operator == sublime.OP_EQUAL:
            if report:
                print("(1) event listener would like to return:", result == operand)
            return result == operand

        if report:
            print("(2) event listener would like to return:", result != operand)
        return result != operand


class PythonInsertImportCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        regions = view.sel()

        for r in regions:
            if r.size() > 0:
                view.erase(r)

        for r in regions:
            view.insert(edit, r.begin(), 'import ')


class PythonImportKeywordAppropriate(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match):
        if key != 'python_import_keyword_appropriate':
            return None

        if len(view.sel()) != 1:
            return False

        return appropriate_point_to_insert_import_keyword(view, view.sel()[0].begin())


class PythonInsertFromCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        regions = view.sel()

        for r in regions:
            if r.size() > 0:
                view.erase(r)

        for r in regions:
            view.insert(edit, r.begin(), 'from ')


class PythonFromKeywordAppropriate(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match):
        if key != 'python_from_keyword_appropriate':
            return None

        if len(view.sel()) != 1:
            return False

        return appropriate_point_to_insert_from_keyword(view, view.sel()[0].begin())


def exists_multiline_selection(view):
    regions = view.sel()
    for r in regions:
        if r.size() > 0:
            row1, _ = view.rowcol(r.begin())
            row2, _ = view.rowcol(r.end())
            if row1 != row2:
                return True
    return False


class NotExistsMultilineSelection(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match):
        if key != 'not_exists_multiline_selection':
            return None
        return not exists_multiline_selection(view)
