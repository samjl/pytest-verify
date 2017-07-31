# pytest-verify Plugin

Pytest plugin API extension to loglevels plugin. 
Adds alternative verification function in place of standard assert 
statements. Additional features over using standard assert
* Ability to continue test after a failing verification (First failing 
verification is raised at the end of the test),
* Ability to raise warnings in addition to failures,
* All verifications results are saved for retrieval/printing at the end of 
the test

## Install

Download and build the [pytest-loglevels](https://github.com/samjl/pytest-loglevels) and pytest-verify packages:

    python setup.py bdist_wheel
(wheel python plugin is required for build step)

Copy dist/pytest_loglevels-... .whl and dist/pytest_verify-... .whl 
to a local python plugin server

    pip install pytest-verify
    
Note: pytest-loglevels will be installed automatically with pytest-verify.

### verify Function Format and Options

Function call format
```python
    verify(msg, fail_condition, *params, **keyword_args)
```

Verification options:
* msg: a message describing the verification being performed
* fail_condition: a lambda function defining the failure condition
* params: 1+ arguments corresponding to the lambda function arguments (in 
same order) 
* raise_assertion (optional, default True): whether to raise an assertion 
immediately upon failure (same behaviour as regular assert)

Traceback options:
* full_method_trace (optional, default False): print an extended traceback 
with the full source of each calling function
* stop_at_test (optional, default True): stop printing the traceback when 
test function is reached (don't descend in to pytest)
* log_level (optional, default None): the log level to assign to the 
verification message (see [pytest-loglevels](https://github.com/samjl/pytest-loglevels) documentation for more information). 
By default the verification message the log level applied is that of the 
previous message +1. After printing the verification message the previous 
log level is restored.

Warning options:
* warning (optional, default None): log as a warning rather than failure
* warn_condition (optional, default None): a lambda function defining the 
warning condition 
* warn_args (optional, default None): warning arguments required for the 
defined lambda condition (These are passed in as a list rather than a 
separate parameter for each)

## Basic Usage

Import the verify function from the pytest namespace:
```python
from pytest import log, verify
```

Basic use in place of a regular assert statement. Behaviour is identical to 
assert, the assertion is raised immediately and the test is torn down and 
ended.
```python
    func = lambda x: x is True  # Create a lambda function for the failure condition
    verify("Check something is true (passes)", func, True)
    verify("Check something is true (fails)", func, False)  # Fails immediately and raises assertion
```

Save but do not raise failed verification:
```python
    verify("Check something is true (fails but does not raise)", func, False,
           raise_assertion=False)
```

## Raising Warnings
As above but set the warning optional argument to raise a failed 
verification as a warningException:
```python
    verify("Check something is true (warning)", func, False, warning=True)
```

## Verifications Including Failure and Warning Conditions
It is also possible to specify a failure condition (that is tested first) 
and a warning condition that is tested only if the failure condition does 
not generate a failure. Example illustrating a variable with three ranges of
values that can create PASS, FAIL and WARNING conditions:
```python
    # Setup the verification so that:
    # if x < 3 pass
    # if 3 <= x <= 10 warns
    # is x > 10 fails
    fail_condition = lambda x: x <= 10
    warn_condition = lambda x: x < 3
    # Pass
    x = 1
    verify("Check x=1 passes", fail_condition, x,
           warn_condition=warn_condition, warn_args=[x])
    # Warning
    x = 10
    verify("Check x=10 warns", fail_condition, x,
           warn_condition=warn_condition, warn_args=[x])
    # Fail
    x = 10.1
    verify("Check x=10.1 fails", fail_condition, x, raise_assertion=False,
           warn_condition=warn_condition, warn_args=[x])
``` 
 
It is also possible to test a completely different object(s) for warning 
if the failure condition is not met, e.g.


## Current Limitations
* Does not re-raise saved failed verifications (test passes when it should 
not), 
* No way to retrieve saved verifications.

## Future Work
* Re-raise saved failed verifications,
* Add pytest hook to report all verifications and any exceptions caught 
during the test,
* Add ability to differentiate between the results fo the test phases 
(setup, call, teardown),
* Verify uses a passed lambda function to test the condition. This is not 
recommended by PEP8 so change to function pointer instead,
* Possible enhancement: make fail and warn condition arguments the same format.
