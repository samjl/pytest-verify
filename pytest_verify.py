import inspect
import pytest
import re
import sys
from collections import OrderedDict

MAX_TRACEBACK_DEPTH = 11
DEBUG_PRINT_SAVED = False


class WarningException(Exception):
    pass


class VerificationException(Exception):
    pass


def pytest_terminal_summary(terminalreporter):
    """ override the terminal summary reporting. """
    print "In pytest_terminal_summary"

    # TODO save any immediately raised assertions

    # Retrieve the saved results and traceback info for any failed
    # verifications.
    print_saved_results()

    saved_tracebacks = Verifications.saved_tracebacks
    pytest.log.high_level_step("Saved tracebacks")
    for saved_tb in saved_tracebacks:
        for line in saved_tb["complete"]:
            pytest.log.step(line)

    # TODO re-raise caught exceptions


def pytest_namespace():
    # Add verify functions to the pytest namespace
    def verify(msg, fail_condition, *params, **keyword_args):
        """Print a message at the highest log level."""
        _verify(msg, fail_condition, *params, **keyword_args)

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
    def __init__(self, type="-", printed="N", raise_immediately="-",
                 tb_index="-", status_printed="N"):
        self.tbIndex = tb_index
        self.type = type
        self.printed = printed
        self.raiseImmediately = raise_immediately
        self.statusPrinted = status_printed

    def format_result_info(self):
        # Format the result to a human readable string.
        if isinstance(self.tbIndex, int):
            if Verifications.saved_tracebacks[int(self.tbIndex)]["raised"]:
                raised = "Y"
            else:
                raised = "N"
        else:
            raised = "-"
        return "{0.tbIndex}:{0.type}.{0.raiseImmediately}.{0.printed}.{1}"\
            .format(self, raised)


def _log_verification(msg, log_level):
    # Log the verification result.
    log_level_restore = pytest.redirect.get_current_level()
    if not log_level:
        log_level_msg = log_level_restore + 1
    else:
        log_level_msg = log_level

    pytest.log.step(msg, log_level_msg)
    pytest.redirect.set_level(log_level_restore)


def _verify(msg, fail_condition, *params, **keyword_args):
    """Perform a verification of a given condition using the parameters
    provided.
    """
    # Parse any keyword arguments
    if "raise_assertion" in keyword_args:
        raise_assertion = keyword_args["raise_assertion"]
    else:
        raise_assertion = True
    if "full_method_trace" in keyword_args:
        full_method_trace = keyword_args["full_method_trace"]
    else:
        full_method_trace = False
    if "stop_at_test" in keyword_args:
        stop_at_test = keyword_args["stop_at_test"]
    else:
        stop_at_test = True
    if "log_level" in keyword_args:
        log_level = keyword_args["log_level"]
    else:
        log_level = None
        # log_level = current_log_level + 1
    if "warning" in keyword_args:
        warning = keyword_args["warning"]
    else:
        warning = False
    if warning:
        raise_assertion = False
    if "warn_condition" in keyword_args:
        warn_condition = keyword_args["warn_condition"]
    else:
        warn_condition = None
    if "warn_args" in keyword_args:
        warn_args = keyword_args["warn_args"]
    else:
        warn_args = None

    fail_condition_parsed = _parse_condition_args(fail_condition, params)
    fail_condition_msg = "{0} ({1[params]}: {1[condition]}, Args: {1[args]})"\
        .format(msg, fail_condition_parsed)
    try:
        assert fail_condition(*params), fail_condition_msg
    except AssertionError:
        msg = _save_failed_verification(msg, fail_condition_msg,
                                        fail_condition_parsed,
                                        full_method_trace, stop_at_test,
                                        raise_assertion, warning=warning)
        _log_verification(msg, log_level)
        if raise_assertion:
            # Raise the exception - test immediately ends
            exc_info = list(sys.exc_info())
            # FIXME deprecated raise format
            raise VerificationException, exc_info[1], exc_info[2]
        return False
    else:
        if warn_condition is not None and warn_args is not None:
            warn_condition_parsed = _parse_condition_args(warn_condition,
                                                          warn_args)
            warning_condition_msg = "{0} ({1[params]}: {1[condition]}, Args: "\
                                    "{1[args]})".format(msg,
                                                        warn_condition_parsed)
            try:
                assert warn_condition(*warn_args), warning_condition_msg
            except AssertionError:
                msg = _save_failed_verification(msg, warning_condition_msg,
                                                warn_condition_parsed,
                                                full_method_trace,
                                                stop_at_test, False,
                                                warning=True)
                _log_verification(msg, log_level)
                # Don't raise warnings during test execution
                return False

        status = "PASS"

        _log_verification("{} - {}".format(fail_condition_msg, status),
                          log_level)

        result_info = ResultInfo(type="P", printed="-", raise_immediately="-",
                                 tb_index="-")

        Verifications.saved_results.append(OrderedDict([('Step',
                                                         pytest.redirect.get_current_l1_msg()),
                                                        ('Message', msg),
                                                        ('Status', status),
                                                        ('Pass Condition', fail_condition_parsed['condition']),
                                                        ('Args', fail_condition_parsed['args']),
                                                        ('Debug', result_info)
                                                        ]))
        return True


def _parse_condition_args(condition, params):
    # Inspect the stack and extract source of the lambda function
    # condition.
    lambda_func = inspect.getsource(condition).strip()
    lambda_search = re.search("(lambda .*): *((.*)\),|(.*))", lambda_func)

    arg_val = []
    for index, arg in enumerate(inspect.getargspec(condition).args):
        arg_val.append("{}: {}".format(arg, params[index]))
    args = ", ".join(arg_val)
    lambda_params = lambda_search.group(1)
    if lambda_search.group(3) is not None:
        lambda_condition = lambda_search.group(3)
    else:
        lambda_condition = lambda_search.group(4)

    return {"condition": lambda_condition, "params": lambda_params,
            "args": args}


def _save_failed_verification(msg, condition_msg, condition_parsed,
                              full_method_trace, stop_at_test, raise_assertion,
                              warning=False):
    # Save a failed verification as FAIL or WARNING.
    # The verification condition, params and arguments are logged and
    # the traceback is saved.
    # A log message is created and returned to the calling function.
    exc_info = list(sys.exc_info())
    result_info = ResultInfo(printed="N")
    if not warning:
        status = "FAIL"
        exc_info[0] = VerificationException
        result_info.type = "F"
        result_info.raiseImmediately = "Y" if raise_assertion else "N"
    else:
        status = "WARNING"
        exc_info[0] = WarningException
        result_info.type = "W"
        result_info.raiseImmediately = "N"
    fail_message = "{}: {} - {}".format(exc_info[0].__name__, condition_msg,
                                        status)
    stack = inspect.stack()
    trace_complete = [fail_message]
    if len(stack) > MAX_TRACEBACK_DEPTH:
        max_traceback_depth = MAX_TRACEBACK_DEPTH
    else:
        max_traceback_depth = len(stack)

    # Just print call lines or source code back to beginning of each
    # calling function (fullMethodTrace)
    for depth in range(3, max_traceback_depth):
        # Skip levels 0 and 1 - this method and verify()
        try:
            # Get the source code, line number for the function
            func_source = inspect.getsourcelines(stack[depth][0])
        except Exception:
            pass
        else:
            # Calling function source file line number
            func_line_number = func_source[1]
            # The calling line of source code within the function
            func_call_source_line = "{0[4][0]}".format(stack[depth])

            stop_keywords = ("runTest", "testfunction", "fixturefunc")
            if stop_at_test and any(item in func_call_source_line.strip() for item in stop_keywords):
                break

            # Line number of calling line
            call_line_number = stack[depth][2]
            # Construct the traceback output for the current traceback depth
            trace_level = ["{0[1]}:{0[2]}:{0[3]}".format(stack[depth])]
            frame_locals = inspect.getargvalues(stack[depth][0]).locals.items()
            trace_level.append(", ".join("{}: {}".format(k, v) for k, v in frame_locals))
            # Print the complete function source code
            if full_method_trace:
                for lineNumber in range(0, call_line_number - func_line_number):
                    source_line = re.sub('[\r\n]', '', func_source[0][lineNumber])
                    trace_level.append(source_line)

            else:
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
                    trace_level.insert(2, source_line)
                    left, right = _parentheses_count(left, right,
                                                     func_source[0][preceding_line_index])
                    preceding_line_index -= 1

            source_line = re.sub('[\r\n]', '', func_call_source_line[1:])
            trace_level.append(">{}".format(source_line))
            # Add to the beginning of the list so the traceback can be
            # printed in reverse order
            trace_complete = trace_level + trace_complete

    # 'raised' keeps track of whether the exception has been raised or not
    # 'tb' is used to re-raise the exception is required at the end of
    # the test. However this traces back to the verify:_verify
    # functions so is not really required.
    Verifications.saved_tracebacks.append({'tb': exc_info,
                                           'complete': trace_complete,
                                           'raised': False})
    # 'Debug' for debugging use only - keep track of whether the
    # verification result has been printed yet
    result_info.tbIndex = len(Verifications.saved_tracebacks) - 1
    Verifications.saved_results.append(OrderedDict([('Step', pytest.redirect.get_current_l1_msg()),
                                                    ('Message', msg),
                                                    ('Status', status),
                                                    ('Pass Condition', condition_parsed['condition']),
                                                    ('Args', condition_parsed['args']),
                                                    ('Debug', result_info)
                                                    ]))
    return fail_message


def print_saved_results(column_key_order="Step", extra_info=False):
    """Format the saved results as a table and print.
    The results are printed in the order they were saved.
    Keyword arguments:
    column_key_order -- specify the column order. Default is to simply
    print the "Step" (top level message) first.
    extra_info -- print an extra column containing the "Debug" field
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
    if not DEBUG_PRINT_SAVED and result["Debug"].printed == "Y":
        return
    line = ""
    for key in column_key_order:
        # Print values in the order defined by column_key_order.
        length = key_val_lengths[key]
        line += '| {0:^{width}} '.format(str(result[key]), width=length)
    for key in result.keys():
        if not extra_info and key == "Debug":
            continue
        key = key.strip()
        if key not in column_key_order:
            length = key_val_lengths[key]
            if key == "Debug":
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
            if not extra_info and key == "Debug":
                continue
            key = key.strip()
            if key not in key_val_lengths:
                key_val_lengths[key] = 0
            if key == "Debug":
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
        if not extra_info and key == "Debug":
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
        if not extra_info and key == "Debug":
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
