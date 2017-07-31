import inspect
import pytest
import re
import sys
from collections import OrderedDict

MAX_TRACEBACK_DEPTH = 11


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
    saved_results = Verifications.saved_results
    pytest.log.high_level_step("Saved results")
    for save_result in saved_results:
        pytest.log.step(save_result)

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
