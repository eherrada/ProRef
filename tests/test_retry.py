"""Tests for app/utils/retry.py"""

import pytest
import time
from unittest.mock import MagicMock, call

from app.utils.retry import retry


class TestRetryDecorator:
    """Test the retry decorator."""

    def test_successful_call_no_retry(self):
        """Function that succeeds should only be called once."""
        mock_func = MagicMock(return_value="success")

        @retry(max_attempts=3, delay=0.01)
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_failure_then_success(self):
        """Function should retry on failure and return on success."""
        mock_func = MagicMock(side_effect=[Exception("fail"), Exception("fail"), "success"])

        @retry(max_attempts=3, delay=0.01)
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_raises_after_max_attempts(self):
        """Should raise exception after max attempts exhausted."""
        mock_func = MagicMock(side_effect=ValueError("always fails"))

        @retry(max_attempts=3, delay=0.01)
        def test_func():
            return mock_func()

        with pytest.raises(ValueError) as exc_info:
            test_func()

        assert "always fails" in str(exc_info.value)
        assert mock_func.call_count == 3

    def test_only_catches_specified_exceptions(self):
        """Should only retry on specified exceptions."""
        mock_func = MagicMock(side_effect=TypeError("wrong type"))

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def test_func():
            return mock_func()

        with pytest.raises(TypeError):
            test_func()

        # Should not retry for TypeError
        assert mock_func.call_count == 1

    def test_exponential_backoff(self):
        """Delay should increase exponentially."""
        call_times = []

        @retry(max_attempts=3, delay=0.05, backoff=2.0)
        def test_func():
            call_times.append(time.time())
            raise Exception("fail")

        with pytest.raises(Exception):
            test_func()

        assert len(call_times) == 3

        # Check delays (with some tolerance)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        assert delay1 >= 0.04  # ~0.05s
        assert delay2 >= 0.08  # ~0.10s (0.05 * 2)

    def test_preserves_function_metadata(self):
        """Decorated function should preserve original metadata."""

        @retry(max_attempts=3, delay=0.01)
        def my_documented_function():
            """This is the docstring."""
            pass

        assert my_documented_function.__name__ == "my_documented_function"
        assert "docstring" in my_documented_function.__doc__

    def test_passes_arguments_correctly(self):
        """Arguments should be passed to the wrapped function."""
        mock_func = MagicMock(return_value="result")

        @retry(max_attempts=3, delay=0.01)
        def test_func(a, b, c=None):
            return mock_func(a, b, c=c)

        result = test_func(1, 2, c=3)

        assert result == "result"
        mock_func.assert_called_once_with(1, 2, c=3)
