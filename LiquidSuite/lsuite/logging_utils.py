"""
Logging utilities for LiquidSuite
Provides consistent logging helpers across the application
"""
import logging
from functools import wraps
from time import time


def get_logger(name):
    """
    Get a logger instance with consistent configuration
    
    Usage:
        from lsuite.logging_utils import get_logger
        logger = get_logger(__name__)
        logger.info("Message")
    """
    return logging.getLogger(name)


def log_execution_time(logger=None):
    """
    Decorator to log function execution time
    
    Usage:
        @log_execution_time()
        def my_function():
            # ... do work
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            start_time = time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time() - start_time
                _logger.debug(f"{func.__name__} completed in {elapsed:.3f}s")
                return result
            except Exception as e:
                elapsed = time() - start_time
                _logger.error(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
                raise
        
        return wrapper
    return decorator


def log_function_call(logger=None, level='DEBUG'):
    """
    Decorator to log function calls with arguments
    
    Usage:
        @log_function_call(level='INFO')
        def process_transactions(count):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            log_level = getattr(logging, level.upper())
            
            # Format arguments
            args_str = ', '.join(repr(arg) for arg in args[:3])  # Limit to first 3 args
            if len(args) > 3:
                args_str += f", ... ({len(args)} total)"
            
            kwargs_str = ', '.join(f"{k}={repr(v)}" for k, v in list(kwargs.items())[:3])
            if len(kwargs) > 3:
                kwargs_str += f", ... ({len(kwargs)} total)"
            
            params = ', '.join(filter(None, [args_str, kwargs_str]))
            
            _logger.log(log_level, f"Calling {func.__name__}({params})")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class TransactionLogger:
    """
    Context manager for logging transaction processing
    
    Usage:
        with TransactionLogger('PDF Upload', logger) as tlog:
            tlog.log('Processing 42 transactions')
            # ... process transactions
            tlog.log(f'Imported {count} transactions')
    """
    
    def __init__(self, operation_name, logger=None):
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger('lsuite')
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time()
        self.logger.info(f"Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time() - self.start_time
        
        if exc_type is None:
            self.logger.info(f"Completed: {self.operation_name} in {elapsed:.2f}s")
        else:
            self.logger.error(
                f"Failed: {self.operation_name} after {elapsed:.2f}s - {exc_val}"
            )
        
        return False  # Re-raise exception if any
    
    def log(self, message, level='INFO'):
        """Log a message during the operation"""
        log_level = getattr(logging, level.upper())
        self.logger.log(log_level, f"[{self.operation_name}] {message}")


# Example usage patterns
if __name__ == '__main__':
    # Setup basic logging for testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    )
    
    logger = get_logger(__name__)
    
    # Example 1: Basic logging
    logger.info("Application started")
    logger.debug("Debug information")
    logger.warning("Warning message")
    
    # Example 2: Execution time decorator
    @log_execution_time()
    def process_data():
        import time
        time.sleep(0.1)
        return "Done"
    
    result = process_data()
    
    # Example 3: Function call decorator
    @log_function_call(level='INFO')
    def import_transactions(count, bank='capitec'):
        return f"Imported {count} from {bank}"
    
    import_transactions(42, bank='tymebank')
    
    # Example 4: Transaction logger
    with TransactionLogger('Test Operation', logger) as tlog:
        tlog.log('Step 1: Loading data')
        tlog.log('Step 2: Processing')
        tlog.log('Step 3: Saving results')
