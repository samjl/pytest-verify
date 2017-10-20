import ConfigParser
import decorator
import inspect
import json
import os
import pkg_resources
import pytest
import re
import sys
import traceback
from collections import OrderedDict
from future.utils import raise_

MAX_TRACEBACK_DEPTH = 20


class DebugFunctionality:
    def __init__(self, name, enabled):
        self.name = name
        self.enabled = enabled


class ConfigOption:
    def __init__(self, value_type, value_default, helptext=""):
        self.value_type = value_type
        self.value = value_default
        if self.value_type is bool:
            help_for_bool = filter(None, [helptext, "Enable: 1/yes/true/on",
                                   "Disable: 0/no/false/off"])
            self.help = ". ".join(help_for_bool)
        else:
            self.help = helptext

DEBUG = {"print-saved": DebugFunctionality("print saved", False),
         "verify": DebugFunctionality("verify", False),
         "not-plugin": DebugFunctionality("not-plugin", False),
         "phases": DebugFunctionality("phases", False),
         "scopes": DebugFunctionality("scopes", False),
         "summary": DebugFunctionality("summary", False)}

CONFIG = {"include-verify-local-vars":
          ConfigOption(bool, True, "Include local variables in tracebacks "
                                   "created by verify function"),
          "include-all-local-vars":
          ConfigOption(bool, False, "Include local variables in all "
                                    "tracebacks. Warning: Printing all locals "
                                    "in a stack trace can easily lead to "
                                    "problems due to errored output"),
          "traceback-stops-at-test-functions":
          ConfigOption(bool, True, "Stop the traceback at the test function"),
          "raise-warnings":
          ConfigOption(bool, True, "Raise warnings (enabled) or just save the "
                                   "result (disabled)"),
          "maximum-traceback-depth":
          ConfigOption(int, 20, "Print up to the maximum limit (integer) of "
                                "stack trace entries"),
          "continue-on-setup-failure":
          ConfigOption(bool, False, "Continue to the test call phase if the "
                                    "setup fails"),
          "continue-on-setup-warning":
          ConfigOption(bool, False, "Continue to the test call phase if the "
                                    "setup warns. To raise a setup warning "
                                    "this must be set to False and "
                                    "raise-warnings set to True")}

SCOPE_ORDER = ("session", "class", "module", "function")


class WarningException(Exception):
    pass


class VerificationException(Exception):
    pass


def pytest_addoption(parser):
    for name, val in CONFIG.iteritems():
        parser.addoption("--{}".format(name),
                         # type=val.value_type,
                         action="store",
                         help=val.help)


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    # Load user defined configuration from file
    config_path = pkg_resources.resource_filename('pytest_verify', '')
    parser = ConfigParser.ConfigParser()
    parser.read(os.path.join(config_path, "config.cfg"))

    for functionality in DEBUG.keys():
        try:
            DEBUG[functionality].enabled = parser.getboolean("debug",
                                                             functionality)
        except Exception as e:
            print e

    for option in CONFIG.keys():
        try:
            if CONFIG[option].value_type is int:
                CONFIG[option].value = parser.getint("general", option)
            else:
                CONFIG[option].value = parser.getboolean("general", option)
        except Exception as e:
            print e

    for name, val in CONFIG.iteritems():
        cmd_line_val = config.getoption("--{}".format(name))
        if cmd_line_val:
            if CONFIG[name].value_type is bool:
                if cmd_line_val.lower() in ("1", "yes", "true", "on"):
                    CONFIG[name].value = True
                elif cmd_line_val.lower() in ("0", "no", "false", "off"):
                    CONFIG[name].value = False
            else:
                CONFIG[name].value = CONFIG[name].value_type(cmd_line_val)

    print "pytest-verify configuration:"
    for option in CONFIG.keys():
        print "{0}: type={1.value_type}, val={1.value}".format(option, CONFIG[
            option])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    _debug_print("SETUP - Starting setup for test {}".format(item.name),
                 DEBUG["phases"])
    _debug_print("SETUP - test {0.name} has fixtures: {0.fixturenames}".format(
        item), DEBUG["scopes"])

    # Set test session globals
    SessionStatus.run_order.append(item.name)  # Save run order TODO remove?
    SessionStatus.test_function = item.name  # same as run_order[-1]
    # Ignore the last fixture name 'request'
    SessionStatus.test_fixtures[item.name] = item.fixturenames[:-1]
    SessionStatus.phase = "setup"
    outcome = yield
    _debug_print("SETUP - Complete {}, outcome: {}".format(item, outcome),
                 DEBUG["phases"])

    raised_exc = outcome.excinfo
    _debug_print("SETUP - Raised exception: {}".format(raised_exc),
                 DEBUG["phases"])

    if raised_exc:
        # Exception has been raised in the setup phase:
        # Could be an exception:
        # 1. raised by a setup function (save exception result),
        # 2. raised by a setup function, caught, saved and re-raised by
        #    the set_scope wrapper (don't re-save).
        stack_trace = traceback.extract_tb(raised_exc[2])
        if not stack_trace[-2][2] == "_set_scope_wrapper" and \
                not stack_trace[-4][2] == "_set_scope_wrapper" and \
                raised_exc[0] != VerificationException and \
                raised_exc[0] != WarningException:
            # Detect an exception NOT already re-raised by the scope
            # wrapper. Save it so it is printed in the results table.
            _save_non_verify_exc(raised_exc)
            _set_saved_raised()
        else:
            _debug_print("SETUP - Found an exception already re-raised by "
                         "wrapper", DEBUG["phases"])
    else:
        # Nothing raised so check if there are any saved results that
        # need to be raised.
        if not CONFIG["continue-on-setup-failure"].value:
            # Re-raise first VerificationException not yet raised.
            # Saved and immediately raised VerificationExceptions are
            # raised here.
            _raise_first_saved_exc_type(VerificationException)
        if not CONFIG["continue-on-setup-warning"].value and \
           CONFIG["raise-warnings"].value:
            # Else re-raise first WarningException not yet raised
            _raise_first_saved_exc_type(WarningException)

    # TODO could this be done at start of pytest_pyfunc_call?
    SessionStatus.phase = "call"


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    _debug_print("CALL - Starting {}".format(pyfuncitem.name), DEBUG["phases"])
    outcome = yield
    _debug_print("CALL - Completed {}, outcome {}".format(pyfuncitem, outcome),
                 DEBUG["phases"])
    # outcome.excinfo may be None or a (cls, val, tb) tuple
    raised_exc = outcome.excinfo
    _debug_print("CALL - Caught exception: {}".format(raised_exc),
                 DEBUG["phases"])
    if raised_exc:
        if raised_exc[0] not in (WarningException, VerificationException):
            # For exceptions other than Warning and Verifications:
            # * save the exceptions details and traceback so they are
            # printed in the final test summary,
            # * re-raise the exception
            _save_non_verify_exc(raised_exc)
            _set_saved_raised()
            raise_(*raised_exc)

    # Re-raise first VerificationException not yet raised
    # Saved and immediately raised VerificationExceptions are raised here.
    _raise_first_saved_exc_type(VerificationException)
    # Else re-raise first WarningException not yet raised
    if CONFIG["raise-warnings"].value:
        _raise_first_saved_exc_type(WarningException)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    _debug_print("TEARDOWN - Starting {}".format(item), DEBUG["phases"])
    SessionStatus.phase = "teardown"
    outcome = yield
    _debug_print("TEARDOWN - completed {}, outcome: {}".format(item, outcome),
                 DEBUG["phases"])

    raised_exc = outcome.excinfo
    _debug_print("TEARDOWN - Raised exception: {}".format(raised_exc),
                 DEBUG["phases"])

    if raised_exc:
        # Exception has been raised in the setup phase:
        # Could be an exception:
        # 1. raised by a setup function (save exception result),
        # 2. raised by a setup function, caught, saved and re-raised by
        #    the set_scope wrapper (don't re-save).
        stack_trace = traceback.extract_tb(raised_exc[2])
        if not stack_trace[-2][2] == "_set_scope_wrapper" and \
                not stack_trace[-4][2] == "_set_scope_wrapper" and \
                raised_exc[0] != VerificationException and \
                raised_exc[0] != WarningException:
            # Detect an exception NOT already re-raised by the scope
            # wrapper. Save it so it is printed in the results table.
            _save_non_verify_exc(raised_exc)
            _set_saved_raised()
        else:
            _debug_print("TEARDOWN - Found an exception already re-raised by "
                         "wrapper", DEBUG["phases"])
    else:
        # Re-raise first VerificationException not yet raised
        # Saved and immediately raised VerificationExceptions are raised here.
        _raise_first_saved_exc_type(VerificationException)
        # Else re-raise first WarningException not yet raised
        if CONFIG["raise-warnings"].value:
            _raise_first_saved_exc_type(WarningException)


def _save_non_verify_exc(raised_exc):
    exc_type = "{}".format(str(raised_exc[0].__name__)[0])
    exc_msg = str(raised_exc[1]).strip().replace("\n", " ")
    _debug_print("Saving caught exception (non-plugin): {}, {}".format(
        exc_type, exc_msg), DEBUG["not-plugin"])
    result_info = ResultInfo(exc_type, True)

    stack_trace = traceback.extract_tb(raised_exc[2])
    frame = raised_exc[2]
    # stack_trace is a list of stack trace tuples for each
    # stack depth (filename, line number, function name*, text)
    # "text" only gets the first line of a call multi-line call
    # stack trace is None if source not available.

    # Get the locals for each traceback entry - required to identify the
    # fixture scope
    # FIXME is there a better way to do this - have to cycle through all
    # frames to get to the most recent
    locals_all_frames = []
    while frame:
        locals_all_frames.append(frame.tb_frame.f_locals)
        frame = frame.tb_next
    # _debug_print("all frames locals: {}".format(locals_all_frames),
    #              DEBUG["not-plugin"])

    trace_complete = []
    for i, tb_level in enumerate(reversed(stack_trace)):
        if CONFIG["traceback-stops-at-test-functions"].value\
                and _trace_end_detected(tb_level[3]):
            break
        trace_complete.insert(0, ">   {0[3]}".format(tb_level))
        if CONFIG["include-all-local-vars"].value:
            trace_complete.insert(0, locals_all_frames[-(i+1)])
        trace_complete.insert(0, "{0[0]}:{0[1]}:{0[2]}".format(tb_level))

    # Divide by 3 as each failure has 3 lines (list entries)
    _debug_print("# of tracebacks: {}".format(len(trace_complete) / 3),
                 DEBUG["not-plugin"])
    _debug_print("length of locals: {}".format(len(locals_all_frames)),
                 DEBUG["not-plugin"])
    if DEBUG["not-plugin"]:
        for line in trace_complete:
            _debug_print(line, DEBUG["not-plugin"])

    fixture_name = None
    fixture_scope = None
    for i, stack_locals in enumerate(reversed(locals_all_frames)):
        # Most recent stack entry first
        # Extract the setup/teardown fixture information if possible
        # keep track of the fixture name and scope
        if "self" in stack_locals:  # teardown
            if isinstance(stack_locals["self"], FixtureDef):
                fixture_name = stack_locals["self"].argname
                fixture_scope = stack_locals["self"].scope
                _debug_print("scope for {} is {} [{}]".format(fixture_name,
                                                              fixture_scope,
                                                              i),
                             DEBUG["not-plugin"])
        if fixture_name:
            break

    _debug_print("saving: {}, {}".format(fixture_name, fixture_scope),
                 DEBUG["not-plugin"])

    # TODO refactor the saved_results format- make it an object
    s_res = Verifications.saved_results
    s_tb = Verifications.saved_tracebacks
    s_tb.append({"type": raised_exc[0],
                 'tb': raised_exc[2],
                 'complete': trace_complete,
                 'raised': True,
                 "res_index": len(s_res)})
    result_info.tb_index = len(s_tb) - 1
    result_info.source_call = [trace_complete[-1]]
    result_info.source_locals = locals_all_frames[-1]
    result_info.source_function = trace_complete[-2]
    result_info.fixture_name = fixture_name
    result_info.scope = fixture_scope
    s_res.append(OrderedDict([('Step', pytest.redirect.get_current_l1_msg()),
                              ('Message', exc_msg),
                              ('Status', "FAIL"),
                              ('Extra Info', result_info)]))


def _raise_first_saved_exc_type(type_to_raise):
    for i, saved_traceback in enumerate(Verifications.saved_tracebacks):
        exc_type = saved_traceback["type"]
        _debug_print("saved traceback index: {}, type: {}, searching for: {}"
                     .format(i, exc_type, type_to_raise), DEBUG["verify"])
        if exc_type == type_to_raise and not saved_traceback["raised"]:
            msg = "{0[Message]} - {0[Status]}".format(
                Verifications.saved_results[saved_traceback["res_index"]])
            tb = saved_traceback["tb"]
            print "Re-raising first saved {}: {} {} {}".\
                format(type_to_raise, exc_type, msg, tb)
            _set_saved_raised()
            raise_(exc_type, msg, tb)  # for python 2 and 3 compatibility


def pytest_report_teststatus(report):
    _debug_print("TEST REPORT FOR {} PHASE".format(report.when),
                 DEBUG["phases"])
    phase_results = get_recent_results(report.when)
    _debug_print("{} - results: {}".format(report.when.upper(), phase_results),
                 DEBUG["summary"])
    report.status = phase_results


def print_new_results(phase):
    for i, s_res in enumerate(Verifications.saved_results):
        res_info = s_res["Extra Info"]
        if res_info.phase == phase and not res_info.printed:
            _debug_print("Valid result ({}) found with info: {}"
                         .format(i, res_info.format_result_info()),
                         DEBUG["scopes"])
            res_info.printed = True


def get_recent_results(phase):
    first_index = None
    for i, s_res in enumerate(Verifications.saved_results):
        res_info = s_res["Extra Info"]
        if not res_info.retrieved and res_info.phase == phase:
            if first_index is None:
                first_index = i
            res_info.retrieved = True

    recent_results_by_type = {}
    if first_index is not None:  # can only be None if the result is a pass
        for index in range(first_index, len(Verifications.saved_results)):
            res_info = Verifications.saved_results[index]["Extra Info"]
            if not res_info.type_code in recent_results_by_type:
                recent_results_by_type[res_info.type_code] = 1
            else:
                recent_results_by_type[res_info.type_code] += 1

    return first_index, len(Verifications.saved_results)-1, \
        recent_results_by_type


def pytest_terminal_summary(terminalreporter):
    """ override the terminal summary reporting. """
    _debug_print("In pytest_terminal_summary", DEBUG["summary"])
    _debug_print("Run order: {}".format(", ".join(SessionStatus.run_order)),
                 DEBUG["summary"])
    for test_name, setup_fixtures in SessionStatus.test_fixtures.iteritems():
        _debug_print("{} depends on setup fixtures: {}"
                     .format(test_name, ", ".join(setup_fixtures)),
                     DEBUG["summary"])

    # Retrieve the saved results and traceback info for any failed
    # verifications.
    print_saved_results(extra_info=True)

    saved_tracebacks = Verifications.saved_tracebacks
    if saved_tracebacks:
        pytest.log.high_level_step("Saved tracebacks")
    for i, saved_tb in enumerate(saved_tracebacks):
        for line in saved_tb["complete"]:
            pytest.log.step(line)
        exc_type = saved_tb["type"]
        pytest.log.step("{0}{1[Message]}".format("{}: ".format(
                        exc_type.__name__) if exc_type else "",
                        Verifications.saved_results[saved_tb["res_index"]]))

    # Collect all the results for each reported phase/scope(/fixture)
    result_by_fixture = OrderedDict()
    _debug_print("Scope/phase saved results summary in executions order:",
                 DEBUG["summary"])
    for saved_result in Verifications.saved_results:
        info = saved_result["Extra Info"]
        key = "{0.fixture_name}:{0.test_function}:{0.phase}:{0.scope}"\
            .format(info)
        if key not in result_by_fixture:
            result_by_fixture[key] = {}
            result_by_fixture[key][info.type_code] = 1
        elif info.type_code not in result_by_fixture[key]:
            result_by_fixture[key][info.type_code] = 1
        else:
            result_by_fixture[key][info.type_code] += 1
    for key, val in result_by_fixture.iteritems():
        _debug_print("{}: {}".format(key, val), DEBUG["summary"])

    pytest_reports = terminalreporter.stats
    reports_total = sum(len(v) for k, v in pytest_reports.items())
    _debug_print("{} reports:".format(reports_total), DEBUG["summary"])
    for report_type, reports in pytest_reports.iteritems():
        for report in reports:
            _debug_print(report, DEBUG["summary"])


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


class SessionStatus:
    # Track the session status
    phase = None  # Current test phase. Possible phases: S(etup),
    # C(all), T(eardown)
    run_order = []  # Test function execution order
    test_fixtures = OrderedDict()

    # Active setup functions
    scopes = {"session": [], "module": [], "class": [], "function": []}
    # Currently active setup or teardown fixture
    test_function = None


class ResultInfo:
    # Instances of ResultInfo used to store information on every
    # verification (originating from the verify function) performed.
    def __init__(self, type_code, raise_immediately):
        # Identify the result
        self.phase = SessionStatus.phase
        self.scope = None
        self.test_function = SessionStatus.test_function
        self.fixture_name = None

        # Type codes:
        # "P": pass, "W": WarningException, "F": VerificationException
        # "A": AssertionError, "O": any Other exception
        self.type_code = type_code
        self.source_function = None
        self.source_call = None
        self.source_locals = None

        self.tb_index = "-"

        self.raise_immediately = raise_immediately

        self.printed = False
        self.retrieved = False

    def format_result_info(self):
        # Format the result to a human readable string.
        if isinstance(self.tb_index, int):
            if Verifications.saved_tracebacks[int(self.tb_index)]["raised"]:
                raised = "Y"
            else:
                raised = "N"
        else:
            raised = "-"
        return "{0.tb_index}:{0.type_code}.{1}.{2}.{3}.({0.phase}:{0.scope}:" \
               "{0.fixture_name})({0.test_function})".format(self,
               "Y" if self.raise_immediately else "N",
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

    _debug_print("Performing verification", DEBUG["verify"])
    _debug_print("Locals: {}".format(inspect.getargvalues(inspect.stack()[1][0]).locals),
                 DEBUG["verify"])

    def warning_init():
        _debug_print("WARNING (fail_condition)", DEBUG["verify"])
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

    if not log_level and pytest.redirect.get_current_level() == 1:
        verify_msg_log_level = 2
    else:
        verify_msg_log_level = log_level
    pytest.log.step("{} - {}".format(msg, status), verify_msg_log_level)
    _save_result(info, msg, status, tb, exc_type, stop_at_test,
                 full_method_trace)

    if not fail_condition and raise_immediately:
        # Raise immediately
        _set_saved_raised()
        raise_(exc_type, msg, tb)
    return True


def _get_complete_traceback(stack, start_depth, stop_at_test,
                            full_method_trace, tb=[]):
    # Print call lines or source code back to beginning of each calling
    # function (fullMethodTrace).
    if len(stack) > MAX_TRACEBACK_DEPTH:
        _debug_print("Length of stack = {}".format(len(stack)),
                     DEBUG["verify"])
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
    except Exception as e:
        _debug_print("{}".format(str(e)), DEBUG["verify"])
        return
    else:
        func_line_number = func_source[1]
        func_call_source_line = "{0[4][0]}".format(stack[depth])
        if stop_at_test and _trace_end_detected(func_call_source_line.strip()):
            return
        call_line_number = stack[depth][2]
        module_line_parent = "{0[1]}:{0[2]}:{0[3]}".format(stack[depth])
        calling_frame_locals = ""
        if CONFIG["include-verify-local-vars"].value\
                or CONFIG["include-all-local-vars"].value:
            try:
                calling_frame_locals = dict(inspect.getargvalues(stack[depth]
                                            [0]).locals.items())
            except Exception as e:
                pytest.log.step("Failed to retrieve local variables for {}".
                                format(module_line_parent), log_level=5)
                _debug_print("{}".format(str(e)), DEBUG["verify"])
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
    if not func_call_line:
        return False
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

    _debug_print("Saving a result of verify function", DEBUG["verify"])
    fixture_name = None
    fixture_scope = None
    if SessionStatus.phase != "call":
        for d in range(depth, depth+6):  # TODO use max tb depth?
            stack_locals = OrderedDict(inspect.getargvalues(stack[d][0]).
                                       locals.items())
            if "self" in stack_locals:  # teardown
                if isinstance(stack_locals["self"], FixtureDef):
                    fixture_name = stack_locals["self"].argname
                    fixture_scope = stack_locals["self"].scope
                    _debug_print("scope for {} is {} [{}]".format(fixture_name,
                                                                  fixture_scope,
                                                                  d),
                                 DEBUG["verify"])
            if fixture_name:
                break

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
    result_info.fixture_name = fixture_name
    result_info.scope = fixture_scope
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
    _debug_print("Column order: {}".format(column_key_order),
                 DEBUG["print-saved"])

    to_print = []
    for saved_result in Verifications.saved_results:
        data = OrderedDict()
        for key, val in saved_result.iteritems():
            if key != "Extra Info":
                data[key] = val
        if extra_info:
            data["phase"] = saved_result["Extra Info"].phase
            data["scope"] = saved_result["Extra Info"].scope
            data["test_function"] = saved_result["Extra Info"].test_function
            data["fixture_name"] = saved_result["Extra Info"].fixture_name
        to_print.append(data)

    key_val_lengths = {}
    if len(to_print) > 0:
        _get_val_lengths(to_print, key_val_lengths)
        headings = _get_key_lengths(key_val_lengths)
        pytest.log.high_level_step("Saved results")
        _print_headings(to_print[0], headings, key_val_lengths,
                        column_key_order)
        for result in to_print:
            _print_result(result, key_val_lengths, column_key_order)


def _print_result(result, key_val_lengths, column_key_order):
    # Print a table row for a single saved result.
    line = ""
    for key in column_key_order:
        # Print values in the order defined by column_key_order.
        length = key_val_lengths[key]
        line += '| {0:^{1}} '.format(str(result[key]), length)
    for key in result.keys():
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


def _get_val_lengths(saved_results, key_val_lengths):
    # Update the maximum field length dictionary based on the length of
    # the values.
    for result in saved_results:
        for key, value in result.items():
            key = key.strip()
            if key not in key_val_lengths:
                key_val_lengths[key] = 0
            if key == "Extra Info":
                length = max(key_val_lengths[key],
                             len(str(value.format_result_info())))
            else:
                length = max(key_val_lengths[key], len(str(value)))
            key_val_lengths[key] = length


def _get_key_lengths(key_val_lengths):
    # Compare the key lengths to the max length of the corresponding
    # value.

    # Dictionary to store the keys (spilt if required) that form the
    # table headings.
    headings = {}
    for key, val in key_val_lengths.iteritems():
        _debug_print("key: {}, key length: {}, length of field from values "
                     "{}".format(key, len(key), val), DEBUG["print-saved"])
        if len(key) > val:
            # The key is longer then the value length
            if ' ' in key or '/' in key:
                # key can be split up to create multi-line heading
                space_indices = [m.start() for m in re.finditer(' ', key)]
                slash_indices = [m.start() for m in re.finditer('/', key)]
                space_indices.extend(slash_indices)
                _debug_print("key can be split @ {}".format(space_indices),
                             DEBUG["print-saved"])
                key_centre_index = int(len(key)/2)
                split_index = min(space_indices, key=lambda x: abs(
                    x - key_centre_index))
                _debug_print('The closest index to the middle ({}) is {}'
                             .format(key_centre_index, split_index),
                             DEBUG["print-saved"])
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
                    column_key_order):
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
    if flag.enabled:
        print "DEBUG({}): {}".format(flag.name, msg)
