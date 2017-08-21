import inspect
import pytest
import re
import sys
import traceback
from collections import OrderedDict
from future.utils import raise_

MAX_TRACEBACK_DEPTH = 20
DEBUG_PRINT_SAVED = False
DEBUG_VERIFY = False
INCLUDE_VERIFY_LOCALS = True
INCLUDE_OTHER_LOCALS = True
STOP_AT_TEST_DEFAULT = True


class WarningException(Exception):
    pass


class VerificationException(Exception):
    pass


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    _debug_print("CALL (test) - Starting test {}".format(pyfuncitem),
                 DEBUG_VERIFY)
    outcome = yield
    _debug_print("CALL (test) - Completed test {}, outcome {}".
                 format(pyfuncitem, outcome), DEBUG_VERIFY)
    # outcome.excinfo may be None or a (cls, val, tb) tuple
    raised_exc = outcome.excinfo
    print "Caught exception: {}".format(raised_exc)
    if raised_exc:
        if raised_exc[0] not in (WarningException, VerificationException):
            exc_type = "{}".format(str(raised_exc[0].__name__)[0])
            exc_msg = str(raised_exc[1]).strip().replace("\n", " ")
            result_info = ResultInfo(exc_type, True)

            stack_trace = traceback.extract_tb(raised_exc[2])
            # stack_trace is a list of stack trace tuples for each
            # stack depth (filename, line number, function name*, text)
            # "text" only gets the first line of a call multi-line call
            # stack trace is None if source not available.
            trace_complete = []
            for tb_level in reversed(stack_trace):
                if STOP_AT_TEST_DEFAULT and _trace_end_detected(tb_level[3].strip()):
                    break
                trace_complete.insert(0, ">   {0[3]}".format(tb_level))

                # Printing all locals in a stack trace can easily lead to
                # problems just due to errored output. That's why it is not
                # implemented in general in Python. Probably okay for
                # controlled purposes like verify traceback to test
                # function and no further.
                # TODO Could possibly truncate the locals?
                # source_locals = ""
                if INCLUDE_OTHER_LOCALS:
                    frame = raised_exc[2]
                    tb_locals = []
                    frame = frame.tb_next
                    while frame:
                        tb_locals.append(frame.tb_frame.f_locals)
                        frame = frame.tb_next
                    trace_complete.insert(0, (", ".join("{}: {}".format(str(k).
                        replace("\n", " "), str(v).replace("\n", " "))
                        for k, v in tb_locals[-1]. iteritems())))

                trace_complete.insert(0, "{0[0]}:{0[1]}:{0[2]}".format(tb_level))

            source_locals = ""
            if INCLUDE_OTHER_LOCALS:
                source_locals = trace_complete[-3]

            s_res = Verifications.saved_results
            s_tb = Verifications.saved_tracebacks
            s_tb.append({"type": raised_exc[0],
                         'tb': raised_exc[2],
                         'complete': trace_complete,
                         'raised': True,
                         "res_index": len(s_res)})
            result_info.tb_index = len(s_tb) - 1
            result_info.source_call = [trace_complete[-1]]
            result_info.source_locals = source_locals
            result_info.source_function = trace_complete[-2]
            s_res.append(OrderedDict([('Step', pytest.redirect.
                                       get_current_l1_msg()),
                                      ('Message', exc_msg),
                                      ('Status', "FAIL"),
                                      ('Extra Info', result_info)]))
            _set_saved_raised()
            raise_(*raised_exc)  # Re-raise the assertion

    # Re-raise caught exceptions
    for i, saved_traceback in enumerate(Verifications.saved_tracebacks):
        exc_type = saved_traceback["type"]
        _debug_print("saved traceback index: {}, type: {}".format(i, exc_type),
                     DEBUG_VERIFY)
        if exc_type:
            msg = "{0[Message]} - {0[Status]}".format(
                Verifications.saved_results[saved_traceback["res_index"]])
            tb = saved_traceback["tb"]
            print "Re-raising first saved exception: {} {} {}".format(
                exc_type, msg, tb)
            if not saved_traceback["raised"]:
                _set_saved_raised()
                raise_(exc_type, msg, tb)  # for python 2 and 3 compatibility


def pytest_terminal_summary(terminalreporter):
    """ override the terminal summary reporting. """
    print "In pytest_terminal_summary"

    # Retrieve the saved results and traceback info for any failed
    # verifications.
    print_saved_results()

    saved_results = Verifications.saved_results
    pytest.log.high_level_step("Saved results")
    for saved_res in saved_results:
        pytest.log.step(saved_res)
        pytest.log.step(saved_res["Extra Info"].format_result_info())
        pytest.log.step(saved_res["Extra Info"].source_function)
        if saved_res["Extra Info"].source_locals:
            pytest.log.step(saved_res["Extra Info"].source_locals)
        for line in saved_res["Extra Info"].source_call:
            pytest.log.step(line)

    saved_tracebacks = Verifications.saved_tracebacks
    pytest.log.high_level_step("Saved tracebacks")
    for i, saved_tb in enumerate(saved_tracebacks):
        pytest.log.step(saved_tb)
        for line in saved_tb["complete"]:
            pytest.log.step(line)
        exc_type = saved_tb["type"]
        pytest.log.step("{0}{1[Message]}".format("{}: ".format(
                        exc_type.__name__) if exc_type else "",
                        Verifications.saved_results[saved_tb["res_index"]]))


def pytest_namespace():
    # Add verify functions to the pytest namespace
    def verify(fail_condition, fail_message, raise_immediately=True,
               warning=False, warn_condition=None, warn_message=None,
               full_method_trace=False, stop_at_test=True, log_level=None):
        """Print a message at the highest log level."""
        _verify(fail_condition, fail_message, raise_immediately,
                warning, warn_condition, warn_message,
                full_method_trace, stop_at_test, log_level)

    def get_saved_results():
        """Development only function.
        """
        return Verifications.saved_results, Verifications.saved_tracebacks

    name = {"verify": verify,
            "get_saved_results": get_saved_results}
    return name


class Verifications:
    # Module level storage of verification results and tracebacks for
    # failures and warnings.
    saved_tracebacks = []
    saved_results = []


class ResultInfo:
    # Instances of ResultInfo used to store information on every
    # verification (originating from the verify function) performed.
    def __init__(self, type_code, raise_immediately):
        # Type codes:
        # "P": pass, "W": WarningException, "F": VerificationException
        # "A": AssertionError, "O": any Other exception
        self.type_code = type_code
        self.raise_immediately = raise_immediately
        self.printed = False
        self.tb_index = "-"
        self.source_function = None
        self.source_call = None
        self.source_locals = None

    def format_result_info(self):
        # Format the result to a human readable string.
        if isinstance(self.tb_index, int):
            if Verifications.saved_tracebacks[int(self.tb_index)]["raised"]:
                raised = "Y"
            else:
                raised = "N"
        else:
            raised = "-"
        return "{0.tb_index}:{0.type_code}.{1}.{2}.{3}"\
            .format(self, "Y" if self.raise_immediately else "N",
                    "Y" if self.printed else "N", raised)


def _log_verification(msg, log_level):
    # Log the verification result.
    log_level_restore = pytest.redirect.get_current_level()
    if not log_level:
        log_level_msg = log_level_restore + 1
    else:
        log_level_msg = log_level

    pytest.log.step(msg, log_level_msg)
    pytest.redirect.set_level(log_level_restore)


def _verify(fail_condition, fail_message, raise_immediately, warning,
            warn_condition, warn_message, full_method_trace,
            stop_at_test, log_level):
    """Perform a verification of a given condition using the parameters
    provided.
    """
    if warning:
        raise_immediately = False

    _debug_print("'*** PERFORMING VERIFICATION ***", DEBUG_VERIFY)
    _debug_print("LOCALS: {}".format(inspect.getargvalues(inspect.stack()[1][0]).locals),
                 DEBUG_VERIFY)

    def warning_init():
        _debug_print("WARNING (fail_condition)", DEBUG_VERIFY)
        info = ResultInfo("W", raise_immediately)
        status = "WARNING"
        exc_type = WarningException
        try:
            raise WarningException()
        except WarningException:
            tb = sys.exc_info()[2]
        return info, status, exc_type, tb

    def failure_init():
        info = ResultInfo("F", raise_immediately)
        status = "FAIL"
        exc_type = VerificationException
        try:
            raise VerificationException()
        except VerificationException:
            tb = sys.exc_info()[2]
        return info, status, exc_type, tb

    def pass_init():
        info = ResultInfo("P", raise_immediately)
        status = "PASS"
        tb = None
        exc_type = None
        return info, status, exc_type, tb

    if not fail_condition:
        msg = fail_message
        if warning:
            info, status, exc_type, tb = warning_init()
        else:
            info, status, exc_type, tb = failure_init()
    elif warn_condition is not None:
        if not warn_condition:
            info, status, exc_type, tb = warning_init()
            msg = warn_message
        else:
            # Passed
            info, status, exc_type, tb = pass_init()
            msg = fail_message
    else:
        # Passed
        info, status, exc_type, tb = pass_init()
        msg = fail_message

    pytest.log.step("{} - {}".format(msg, status))
    _save_result(info, msg, status, tb, exc_type, stop_at_test,
                 full_method_trace)

    if not fail_condition and raise_immediately:
        # Raise immediately
        raise_(exc_type, msg, tb)
    return True


def _get_complete_traceback(stack, start_depth, stop_at_test,
                            full_method_trace, tb=[]):
    # Print call lines or source code back to beginning of each calling
    # function (fullMethodTrace).
    if len(stack) > MAX_TRACEBACK_DEPTH:
        _debug_print("Length of stack = {}".format(len(stack)), DEBUG_VERIFY)
        max_traceback_depth = MAX_TRACEBACK_DEPTH
    else:
        max_traceback_depth = len(stack)

    for depth in range(start_depth, max_traceback_depth):  # Already got 3
        calling_func = _get_calling_func(stack, depth, stop_at_test,
                                         full_method_trace)
        if calling_func:
            source_function, source_locals, source_call = calling_func
            tb_new = [source_function]
            if source_locals:
                tb_new.append(source_locals)
            tb_new.extend(source_call)
            tb[0:0] = tb_new
        else:
            break
    return tb


def _get_calling_func(stack, depth, stop_at_test, full_method_trace):
    calling_source = []
    try:
        func_source = inspect.getsourcelines(stack[depth][0])
    except Exception:
        return
    else:
        func_line_number = func_source[1]
        func_call_source_line = "{0[4][0]}".format(stack[depth])
        if stop_at_test and _trace_end_detected(func_call_source_line.strip()):
            return
        call_line_number = stack[depth][2]
        module_line_parent = "{0[1]}:{0[2]}:{0[3]}".format(stack[depth])
        calling_frame_locals = ""
        if INCLUDE_VERIFY_LOCALS:
            try:
                args = inspect.getargvalues(stack[depth][0]).locals.items()
                calling_frame_locals = (", ".join("{}: {}".format(k, v)
                                        for k, v in args))
            except Exception:
                pytest.log.step("Failed to retrieve local variables for {}".
                                format(module_line_parent), log_level=5)
        _debug_print("CALL: {}".format(module_line_parent), DEBUG_VERIFY)
        if full_method_trace:
            for lineNumber in range(0, call_line_number - func_line_number):
                source_line = re.sub('[\r\n]', '', func_source[0][lineNumber])
                calling_source.append(source_line)
            source_line = re.sub('[\r\n]', '', func_source[0][
                call_line_number-func_line_number][1:])
            calling_source.append(">{}".format(source_line))
        else:
            calling_source = _get_call_source(func_source,
                                              func_call_source_line,
                                              call_line_number,
                                              func_line_number)
        return module_line_parent, calling_frame_locals, calling_source


def _trace_end_detected(func_call_line):
    # Check for the stop keywords in the function call source line
    # (traceback). Returns True if keyword found and traceback is
    # complete, False otherwise.
    stop_keywords = ("runTest", "testfunction", "fixturefunc")
    return any(item in func_call_line for item in stop_keywords)


def _save_result(result_info, msg, status, tb, exc_type, stop_at_test,
                 full_method_trace):
    """Save a result of verify/_verify.
    Items to save:
    Saved result - Step,
                   Message,
                   Status,
                   Extra Info (instance of ResultInfo)
    Traceback - type,
                tb,
                complete,
                raised,
                res_index
    """
    stack = inspect.stack()
    depth = 3

    r = result_info
    r.source_function, r.source_locals, r.source_call = \
        _get_calling_func(stack, depth, True, full_method_trace)
    tb_depth_1 = [r.source_function]
    if r.source_locals:
        tb_depth_1.append(r.source_locals)
    tb_depth_1.extend(r.source_call)

    depth += 1
    s_res = Verifications.saved_results
    if result_info.type_code == "F" or result_info.type_code == "W":
        # Types processed by this function are "P", "F" and "W"
        trace_complete = _get_complete_traceback(stack, depth, stop_at_test,
                                                 full_method_trace,
                                                 tb=tb_depth_1)

        s_tb = Verifications.saved_tracebacks
        s_tb.append({"type": exc_type,
                     'tb': tb,
                     'complete': trace_complete,
                     'raised': False,
                     "res_index": len(s_res)})
        result_info.tb_index = len(s_tb) - 1

    s_res.append(OrderedDict([('Step', pytest.redirect.get_current_l1_msg()),
                              ('Message', msg),
                              ('Status', status),
                              ('Extra Info', result_info)]))


def _set_saved_raised():
    # Set saved traceback as raised so they are not subsequently raised
    # again.
    for saved_traceback in Verifications.saved_tracebacks:
        saved_traceback["raised"] = True


def _get_call_source(func_source, func_call_source_line, call_line_number,
                     func_line_number):
    trace_level = []
    # Check if the source line parentheses match (equal
    # number of "(" and ")" characters)
    left = 0
    right = 0

    def _parentheses_count(left, right, line):
        left += line.count("(")
        right += line.count(")")
        return left, right
    left, right = _parentheses_count(left, right,
                                     func_call_source_line)
    preceding_line_index = call_line_number - func_line_number - 1

    while left != right and preceding_line_index > call_line_number - func_line_number - 10:
        source_line = re.sub('[\r\n]', '', func_source[0][preceding_line_index])
        trace_level.insert(0, source_line)
        left, right = _parentheses_count(left, right,
                                         func_source[0][preceding_line_index])
        preceding_line_index -= 1

    source_line = re.sub('[\r\n]', '', func_call_source_line[1:])
    trace_level.append(">{}".format(source_line))
    return trace_level


def print_saved_results(column_key_order="Step", extra_info=False):
    """Format the saved results as a table and print.
    The results are printed in the order they were saved.
    Keyword arguments:
    column_key_order -- specify the column order. Default is to simply
    print the "Step" (top level message) first.
    extra_info -- print an extra column containing the "Extra Info" field
    values.
    """
    if not isinstance(column_key_order, (tuple, list)):
        column_key_order = [column_key_order]
    _debug_print("Column order: {}".format(column_key_order), DEBUG_PRINT_SAVED)

    key_val_lengths = {}
    if len(Verifications.saved_results) > 0:
        _get_val_lengths(Verifications.saved_results, key_val_lengths,
                         extra_info)
        headings = _get_key_lengths(key_val_lengths, extra_info)
        pytest.log.high_level_step("Saved results")
        _print_headings(Verifications.saved_results[0], headings,
                        key_val_lengths, column_key_order, extra_info)

        for result in Verifications.saved_results:
            _print_result(result, key_val_lengths, column_key_order,
                          extra_info)


def _print_result(result, key_val_lengths, column_key_order, extra_info):
    # Print a table row for a single saved result.
    if not DEBUG_PRINT_SAVED and result["Extra Info"].printed:
        return
    line = ""
    for key in column_key_order:
        # Print values in the order defined by column_key_order.
        length = key_val_lengths[key]
        line += '| {0:^{width}} '.format(str(result[key]), width=length)
    for key in result.keys():
        if not extra_info and key == "Extra Info":
            continue
        key = key.strip()
        if key not in column_key_order:
            length = key_val_lengths[key]
            if key == "Extra Info":
                val = result[key].format_result_info()
            else:
                val = result[key]
            line += '| {0:^{width}} '.format(str(val), width=length)
    line += "|"
    pytest.log.detail_step(line)


def _get_val_lengths(saved_results, key_val_lengths, extra_info):
    # Update the maximum field length dictionary based on the length of
    # the values.
    for result in saved_results:
        for key, value in result.items():
            if not extra_info and key == "Extra Info":
                continue
            key = key.strip()
            if key not in key_val_lengths:
                key_val_lengths[key] = 0
            if key == "Extra Info":
                length = max(key_val_lengths[key],
                             len(str(value.format_result_info())))
            else:
                length = max(key_val_lengths[key], len(str(value)))
            key_val_lengths[key] = length


def _get_key_lengths(key_val_lengths, extra_info):
    # Compare the key lengths to the max length of the corresponding
    # value.

    # Dictionary to store the keys (spilt if required) that form the
    # table headings.
    headings = {}
    for key, val in key_val_lengths.iteritems():
        _debug_print("key: {}, key length: {}, length of field from values "
                     "{}".format(key, len(key), val), DEBUG_PRINT_SAVED)
        if not extra_info and key == "Extra Info":
            continue
        if len(key) > val:
            # The key is longer then the value length
            if ' ' in key or '/' in key:
                # key can be split up to create multi-line heading
                space_indices = [m.start() for m in re.finditer(' ', key)]
                slash_indices = [m.start() for m in re.finditer('/', key)]
                space_indices.extend(slash_indices)
                _debug_print("key can be split @ {}".format(space_indices),
                             DEBUG_PRINT_SAVED)
                key_centre_index = int(len(key)/2)
                split_index = min(space_indices, key=lambda x: abs(
                    x - key_centre_index))
                _debug_print('The closest index to the middle ({}) is {}'
                             .format(key_centre_index, split_index),
                             DEBUG_PRINT_SAVED)
                # Add the split key string as two strings (line 1, line
                # 2) to the headings dictionary.
                headings[key] = [key[:split_index+1].strip(),
                                 key[split_index+1:]]
                # Update the lengths dictionary with the shortened
                # headings (The max length of the two lines)
                key_val_lengths[key] = max(len(headings[key][0]),
                                           len(headings[key][1]),
                                           key_val_lengths[key])
            # and can't be split
            else:
                key_val_lengths[key] = max(len(key), key_val_lengths[key])
                headings[key] = [key, ""]
        else:
            key_val_lengths[key] = max(len(key), key_val_lengths[key])
            headings[key] = [key, ""]

    return headings


def _get_line_length(key_val_lengths):
    # Return the line length based upon the max key/value lengths of
    # the saved results.
    line_length = 0
    # Calculate the line length (max length of all keys/values)
    for key in key_val_lengths:
        line_length += key_val_lengths[key] + 3
    line_length += 1
    return line_length


def _print_headings(first_result, headings, key_val_lengths,
                    column_key_order, extra_info):
    # Print the headings of the saved results table (keys of
    # dictionaries stored in saved_results).
    lines = ["", "", ""]
    line_length = _get_line_length(key_val_lengths)
    pytest.log.detail_step("_" * line_length)
    for key in column_key_order:
        field_length = key_val_lengths[key]
        for line_index in (0, 1):
            lines[line_index] += '| ' + '{0:^{width}}'.format(
                headings[key][line_index], width=field_length) + ' '
        lines[2] += '|-' + '-'*field_length + '-'
    for key, value in first_result.items():
        if not extra_info and key == "Extra Info":
            continue
        key = key.strip()
        if not (((type(column_key_order) is list) and
                 (key in column_key_order)) or
                ((type(column_key_order) is not list) and
                 (key == column_key_order))):
            field_length = key_val_lengths[key]
            for line_index in (0, 1):
                lines[line_index] += ('| ' + '{0:^{width}}'.format(
                    headings[key][line_index], width=field_length) + ' ')
            lines[2] += ('|-' + '-'*field_length + '-')
    for line in lines:
        line += "|"
        pytest.log.detail_step(line)


def _debug_print(msg, flag):
    # Print a debug message if the corresponding flag is set.
    if flag:
        print msg
