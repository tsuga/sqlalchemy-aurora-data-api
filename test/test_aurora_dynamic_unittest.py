"""
Dynamic Unittest Generation for Aurora Data API SQLAlchemy Testing
This module dynamically generates unittest.TestCase classes for all discovered SQLAlchemy tests
to provide VS Code Testing integration with full test visibility.
"""

import unittest
import sys
import os
import pkgutil
import inspect
from typing import Dict, List, Tuple, Any

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Setup environment and dialect
env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.pg.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                os.environ[key] = value

from sqlalchemy_aurora_data_api import register_dialects
register_dialects()

# Configure SQLAlchemy testing
from sqlalchemy.testing import config
from sqlalchemy import create_engine
from sqlalchemy.testing.requirements import SuiteRequirements
from sqlalchemy.testing import exclusions

# Setup database
db_name = os.environ.get('AURORA_DB_NAME', 'postgres')
cluster_arn = os.environ.get('AURORA_CLUSTER_ARN', '')
secret_arn = os.environ.get('SECRET_ARN', '')

db_url = (f"postgresql+auroradataapi://:@/{db_name}"
          f"?aurora_cluster_arn={cluster_arn}"
          f"&secret_arn={secret_arn}")

engine = create_engine(db_url)
config.db = engine

class AuroraRequirements(SuiteRequirements):
    @property
    def savepoints(self):
        return exclusions.closed()
    
    @property
    def two_phase_transactions(self):
        return exclusions.closed()
    
    @property
    def independent_connections(self):
        return exclusions.closed()
    
    @property
    def isolated_connections(self):
        return exclusions.closed()

config.requirements = AuroraRequirements()

class SQLAlchemyTestSuiteDiscovery:
    """Dynamic discovery of all SQLAlchemy test suites"""
    
    @staticmethod
    def discover_all_test_suites() -> Dict[str, List[Tuple[str, type, int]]]:
        """
        Dynamically discover all SQLAlchemy test suite classes
        
        Returns:
            Dict mapping module names to list of (class_name, class_obj, method_count) tuples
        """
        import sqlalchemy.testing.suite
        
        discovered_suites = {}
        
        for importer, modname, ispkg in pkgutil.iter_modules(
            sqlalchemy.testing.suite.__path__, 
            'sqlalchemy.testing.suite.'
        ):
            try:
                module = __import__(modname, fromlist=[''])
                test_classes = []
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Look for SQLAlchemy test classes
                    if (hasattr(obj, '__mro__') and 
                        any(base.__name__ in ['TestBase', 'TablesTest'] for base in obj.__mro__) and
                        name not in ['TestBase', 'TablesTest'] and
                        obj.__module__ == modname):  # Only classes defined in this module
                        
                        # Count test methods
                        test_methods = [m for m in dir(obj) if m.startswith('test_') and callable(getattr(obj, m))]
                        if test_methods:
                            test_classes.append((name, obj, len(test_methods)))
                
                if test_classes:
                    discovered_suites[modname] = test_classes
                    
            except Exception as e:
                print(f"Warning: Could not import {modname}: {e}")
        
        return discovered_suites

class DynamicTestGenerator:
    """Generates unittest.TestCase classes dynamically from discovered SQLAlchemy tests"""
    
    def __init__(self):
        self.discovery = SQLAlchemyTestSuiteDiscovery()
        self.discovered_suites = self.discovery.discover_all_test_suites()
        self.requirements = AuroraRequirements()
        
    def generate_unittest_classes(self):
        """Generate unittest.TestCase classes for all discovered SQLAlchemy tests"""
        generated_classes = {}
        
        for module_name, classes in self.discovered_suites.items():
            suite_name = module_name.split('.')[-1]  # e.g., 'test_insert'
            
            for class_name, test_class, method_count in classes:
                unittest_class_name = f"{suite_name}__{class_name}"
                
                # Create unittest wrapper class
                unittest_class = self._create_unittest_wrapper(
                    unittest_class_name, 
                    module_name, 
                    class_name, 
                    test_class
                )
                
                generated_classes[unittest_class_name] = unittest_class
                
        return generated_classes
    
    def _create_unittest_wrapper(self, unittest_class_name, module_name, class_name, test_class):
        """Create a unittest.TestCase wrapper for a SQLAlchemy test class"""
        
        class_attrs = {
            '__module__': __name__,
            '__qualname__': unittest_class_name,
            '_sqlalchemy_module': module_name,
            '_sqlalchemy_class': class_name,
            '_sqlalchemy_test_class': test_class,
        }
        
        # Get all test methods from the SQLAlchemy test class
        test_methods = [name for name in dir(test_class) if name.startswith('test_')]
        
        # Create unittest test methods dynamically
        for method_name in test_methods:
            test_method = self._create_unittest_test_method(module_name, class_name, method_name)
            class_attrs[method_name] = test_method
        
        # Create the unittest class dynamically
        unittest_wrapper_class = type(unittest_class_name, (unittest.TestCase,), class_attrs)
        
        return unittest_wrapper_class
    
    def _create_unittest_test_method(self, module_name, class_name, method_name):
        """Create a single unittest test method that wraps a SQLAlchemy test"""
        
        def test_method(self):
            """Dynamically generated unittest method that executes SQLAlchemy test"""
            try:
                # Import SQLAlchemy testing framework
                from sqlalchemy.testing import config, fixtures
                
                # Get requirements instance
                requirements = AuroraRequirements()
                
                # Import the SQLAlchemy test module
                test_module = __import__(module_name, fromlist=[class_name])
                sqlalchemy_test_class = getattr(test_module, class_name)
                
                # Create Aurora-specific version that properly inherits TestBase
                aurora_class_name = f"Aurora{class_name}"
                
                # Build proper class hierarchy - ensure TestBase is in the MRO
                base_classes = []
                if fixtures.TestBase not in sqlalchemy_test_class.__mro__:
                    base_classes.append(fixtures.TestBase)
                base_classes.append(sqlalchemy_test_class)
                
                aurora_test_class = type(aurora_class_name, tuple(base_classes), {
                    '__only_on__': ('postgresql+auroradataapi',),
                    'requirements': requirements,
                    '__module__': test_module.__name__,
                    '__backend__': True
                })
                
                # Use simplified approach similar to our working test runner
                from sqlalchemy import MetaData
                
                # Create test instance
                test_instance = aurora_test_class()
                
                # Create fresh metadata for this test
                metadata = MetaData()
                
                # Define tables if the test class has table definitions
                if hasattr(aurora_test_class, 'define_tables'):
                    aurora_test_class.define_tables(metadata)
                    # Create tables in database
                    metadata.create_all(config.db)
                
                try:
                    # Get the test method
                    test_method_obj = getattr(test_instance, method_name)
                    
                    # Execute with a fresh connection
                    with config.db.connect() as conn:
                        # Try to execute the test method with connection
                        test_method_obj(conn)
                        
                    # If we get here, the test passed
                    self.assertTrue(True, f"SQLAlchemy test {class_name}.{method_name} executed successfully")
                    
                finally:
                    # Clean up tables
                    if metadata.tables:
                        metadata.drop_all(config.db)
                
            except Exception as e:
                # Provide detailed error information  
                error_msg = f"SQLAlchemy test {class_name}.{method_name} failed: {str(e)}"
                self.fail(error_msg)
        
        # Set proper method name and documentation
        test_method.__name__ = method_name
        test_method.__doc__ = f"Execute SQLAlchemy {class_name}.{method_name} against Aurora Data API"
        
        return test_method


# Initialize the generator and create all unittest classes
print("🔍 Dynamically generating unittest wrappers for SQLAlchemy tests...")
generator = DynamicTestGenerator()
generated_classes = generator.generate_unittest_classes()

# Add all generated classes to the module namespace
for class_name, test_class in generated_classes.items():
    globals()[class_name] = test_class

print(f"✅ Generated {len(generated_classes)} unittest wrapper classes")
print(f"📊 Total SQLAlchemy tests available: {sum(len(classes) for classes in generator.discovered_suites.values())}")

# Create a summary test class for overview
class AuroraSQLAlchemyTestSummary(unittest.TestCase):
    """Summary information about dynamically generated SQLAlchemy tests"""
    
    def test_dynamic_generation_summary(self):
        """Display summary of dynamically generated tests"""
        generator = DynamicTestGenerator()
        total_suites = len(generator.discovered_suites)
        total_classes = sum(len(classes) for classes in generator.discovered_suites.values())
        total_methods = sum(method_count for classes in generator.discovered_suites.values() 
                           for _, _, method_count in classes)
        
        print(f"\n=== Aurora SQLAlchemy Dynamic Test Generation Summary ===")
        print(f"📦 Test Suite Modules: {total_suites}")
        print(f"🏗️  Test Classes: {total_classes}")
        print(f"🧪 Test Methods: {total_methods}")
        print(f"✨ Unittest Wrappers Generated: {len(generated_classes)}")
        print("🎯 All tests are now visible in VS Code Testing!")
        
        self.assertGreater(total_methods, 500, "Should have discovered 500+ test methods")
        self.assertGreater(len(generated_classes), 80, "Should have generated 80+ unittest classes")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)