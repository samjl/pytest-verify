# pytest-verify Plugin

Pytest plugin API extension to loglevels plugin.
Adds alternative verification (verify) function in place of standard assert statements.
Additional features over using standard assert:
* Ability to continue test after a failing verification
(the first saved failing/warning verification is raised at the end of the test),
* Ability to raise warnings instead of failures,
* Ability to test a failure condition and if that passes a additional warning condition,
* All verifications results and tracebacks are saved for retrieval/printing at the end of the test.

## Install

Download and build the [pytest-loglevels](https://github.com/samjl/pytest-loglevels) and
pytest-verify packages:

    python setup.py bdist_wheel
(wheel python plugin is required for build step)

Copy dist/pytest_loglevels-... .whl and dist/pytest_verify-... .whl to a local python plugin server

    pip install pytest-verify
    
Note: pytest-loglevels will be installed automatically with pytest-verify.

### verify Function Format and Options

Function call format
```python
verify(fail_condition, fail_message, raise_assertion=True,
       warning=False, warn_condition=None, warn_message=None,
       full_method_trace=False, stop_at_test=True, log_level=None)
```

Verification options:
* fail_condition:
an expression that if it evaluates to False raises a VerificationException
(or WarningException is warning is set to True).
* fail_message:
a message describing the verification being performed (requires fail_condition to be defined).
* raise_assertion (optional, default True):
whether to raise an assertion immediately upon failure (same behaviour as regular assert).
* warning (optional, default None):
raise the fail_condition as a WarningException rather than VerificationException.

Warning options:
* warn_condition (optional, default None):
if fail_condition evaluates to True test this condition for a warning (cannot be used in addition to warning parameter).
Raises WarningException if expression evaluates to False.
* warn_message:
a message describing the warning condition being verified (requires warn_condition to be defined).

Traceback options:
* full_method_trace (optional, default False):
print an extended traceback with the full source of each calling function.
* stop_at_test (optional, default True):
stop printing the traceback when test function is reached (don't descend in to pytest).
* log_level (optional, default None):
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
the assertion is raised immediately and the test is torn down and ended.
```python
    # expected to pass:
    x = True
    verify(x is True, "Check something is true (passes)")
    # expected to fail immediately and raise assertion:
    y = False
    verify(y is True, "Check something is true (fails)")
```

Save but do not raise failed verification:
```python
    verify(y is True, "Check something is true (fails)", raise_assertion=False)
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

## Current Limitations
* The first saved result other than a pass is raised at the end of the test.
This means a warning may be raised over a failure. See suture work to always raise failures first.
* failure/warning_message parameters expect a string rather than an expression
(assert condition prints result of an expression as the exception message).
* Currently raises the first exception regardless of which test function raised it
i.e. only correct for the test function that raises the first exception.
A check is required to ensure any exceptions from previous tests are not re-raised
(they still need to be saved to print in the final summary).

## Future Work
* Save any exceptions other than VerificationException and WarningExceptions that are caught at the end of the call phase.
* When re-raising saved results at the end of the test always raise any failures before raising a saved warning
(even if warning was initially raised first).
* Add ability to differentiate between the results of the test phases (setup, call, teardown).
