import unittest


class Stdlib(unittest.TestCase):
    def test_types_folder_does_not_shadow_stdlib(self):
        import types
        self.assertTrue(hasattr(types, "ModuleType"), "types/ at the root became a package: remove its __init__.py")
