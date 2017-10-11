# pytest-verify Plugin

Pytest plugin API extension to loglevels plugin.
Adds alternative verification (verify) function in place of standard assert statements.
Additional features over using standard assert:
- Ability to continue test after a failing verification
(the first saved failing/warning verification is raised at the end of the test)
- Ability to raise warnings instead of failures
- Ability to test a failure condition and if that passes a additional warning condition
- All verifications results and tracebacks are saved for retrieval/printing at the end of the test

- Ability to track the status of each test phases (setup, call, teardown)

  and further, the ability to track the status of individual setup and teardown functions

## Install

Download and build the [pytest-loglevels](https://github.com/samjl/pytest-loglevels) and
[pytest-verify](https://github.com/samjl/pytest-verify) packages:

    python setup.py bdist_wheel
(wheel python plugin is required for build step)

Copy dist/pytest_loglevels-... .whl and dist/pytest_verify-... .whl to a local python plugin server

Install the pytest-verify plugin:

    pip install pytest-verify
    
Note: pytest-loglevels will be installed automatically with pytest-verify.

### verify Function Format and Options

Function call format
```python
verify(fail_condition, fail_message, raise_immediately=True,
       warning=False, warn_condition=None, warn_message=None,
       full_method_trace=False, stop_at_test=True, log_level=None)
```

Verification options:
- fail_condition:
an expression that if it evaluates to False raises a VerificationException
(or WarningException is warning is set to True).
- fail_message:
a message describing the verification being performed (requires fail_condition to be defined).
- raise_immediately (optional, default True):
whether to raise an exception immediately upon failure (same behaviour as regular assert).
- warning (optional, default None):
raise the fail_condition as a WarningException rather than VerificationException.

Warning options:
- warn_condition (optional, default None):
if fail_condition evaluates to True test this condition for a warning (cannot be used in addition to warning parameter).
Raises WarningException if expression evaluates to False.
- warn_message:
a message describing the warning condition being verified (requires warn_condition to be defined).

Traceback options:
- full_method_trace (optional, default False):
print an extended traceback with the full source of each calling function.
- stop_at_test (optional, default True):
stop printing the traceback when test function is reached (don't descend in to pytest).
- log_level (optional, default None):
the log level to assign to the verification message
(see [pytest-loglevels](https://github.com/samjl/pytest-loglevels) documentation for more information).
By default the verification message the log level applied is that of the previous message +1.
After printing the verification message the previous log level is restored.

## Basic Usage

Import the verify function from the pytest namespace:
```python
from pytest import log, verify
```

Basic use in place of a regular assert statement. Behaviour is identical to assert,
the exception is raised immediately and the test is torn down and ended.
```python
# expected to pass:
x = True
verify(x is True, "Check something is true (passes)")
# expected to fail immediately and raise exception:
y = False
verify(y is True, "Check something is true (fails)")
```

Save but do not raise failed verification:
```python
verify(y is True, "Check something is true (fails)", raise_immediately=False)
```

## Raising Warnings
As above but set the warning optional argument to raise a failed verification as a warningException:
```python
verify(y is True, "Check something is true (warning)", warning=True)
```

## Verifications Including Failure and Warning Conditions
It is also possible to specify a failure condition (that is tested first) and
a warning condition that is tested only if the failure condition does not generate a failure.
Example illustrating a variable with three ranges of values that can create PASS,
FAIL and WARNING conditions:
```python
# Setup the verification so that:
# if x < 3 pass
# if 3 <= x <= 10 warns
# is x > 10 fails

# Pass
x = 1
verify(x <= 10, "Check x is less than or equal to 10",
       warn_condition=x < 3, warn_message="Check x is less than 3")
# Warning
y = 10
verify(y <= 10, "Check y is less than or equal to 10",
       warn_condition=y < 3, warn_message="Check y is less than 3")
# Fail
z = 10.1
verify(z <= 10, "Check z is less than or equal to 10",
       warn_condition=z < 3, warn_message="Check z is less than 3")
``` 
 
It is also possible to test a completely different object(s) for warning if the failure condition is not met,
e.g.
```python
x = True
y = False
verify(x is True, "test x is True (initial pass)",
       warn_condition=y is True,
       warn_message="test y is True (initial pass->warning)")
```

## Decorating Setup and Teardown Fixtures
The plugin tracks the verification (and regular python assertions) results with respect to the:
- Test phase. setup/call(test function)/teardown
- Fixture scope. The scope of the setup/teardown fixture. This can be function, class, module or session.
See pytest documentation [here](https://docs.pytest.org/en/latest/fixture.html)

and also if the set_ and clear_scope wrappers are used, to decorate the setup and teardown functions respectively:
- The setup/teardown functions. Each setup and teardown result is associated with the corresponding setup or teardown function name 

Below is an example setup and teardown fixture that decorates the
setup function setup_something with the set_scope wrapper and the
teardown function teardown_something with the clear_scope wrapper:
```python
from pytest import (
    log,
    set_scope,
    clear_scope,
    fixture
)

@fixture(scope='function')
def function_scope_setup_and_teardown(request):
    @clear_scope(request)
    def teardown_something():
        log.high_level_step("Performing function scope teardown")
        # Teardown code here        
    request.addfinalizer(teardown_something)

    @set_scope(request)
    def setup_something():
        log.high_level_step("Performing function scope setup")
        # Setup code here        
    setup_something()
```

Note: The set_ and clear_scope decorators are not necessary for normal operation and simply improve the status reporting.

## Plugin Configuration
The plugin can be configured by editing the config.cfg file created when the plugin is installed.
(This is created within the site-packages/pytest-verify directory).
The options in the configuration file may also be overridden by specifying them in the command line. 

### Configuration options
- include-verify-local-vars (Boolean):
Include local variables in tracebacks created by verify function.
- include-all-local-vars (Boolean):
Include local variables in all tracebacks. Warning: Printing all locals in a stack trace can easily lead to problems due to errored output.
- traceback-stops-at-test-functions (Boolean):
Stop the traceback at the test function.
- raise-warnings (Boolean):
Raise warnings (enabled) or just save the result (disabled).
- continue-on-setup-failure (Boolean):
Continue to the test call phase if the setup fails.
- continue-on-setup-warning (Boolean):
Continue to the test call phase if the setup warns. To raise a setup warning this must be set to False and raise-warnings set to True.

Note: Boolean options may be entered as 1/yes/true/on or 0/no/false/off.

- maximum-traceback-depth (Integer):
Print up to the maximum limit (integer) of stack trace entries.

## Current Limitations
- failure/warning_message parameters expect a string rather than an expression
(assert condition prints result of an expression as the exception message).

## Future Work
Complete results table: add traceback to rows that warn/fail

Highlight active setups and their status for each test function result

Update the pytest status line using the new information (e.g 1 setup-warning, 2 passes)

Enhancement: test to decide whether teardown is required if test passes
(useful when using the same function scoped setup for multiple test functions)

Enhancement: test may inspect previous test result to check if (function) setup is required.

Possible enhancement - configuration for each setup/teardown fixture: 
- continue-to-call: continue to the test function call phase regardless of the setup result
- no-setup-if-prev-pass/warn: don't setup again (function scope) is previous test passed or warned
- teardown-on-pass: whether to teardown or not is the test passes (setup and call)
- teardown-on-warning: whether to teardown or not based on warnings (in setup and call)  
- raise-setup/call/teardown-warnings: more fine grained scope control over raising warnings
