import pytest
import pathlib

from django.core.management import call_command


# Mark the tests in relevant packages (paths)
def pytest_collection_modifyitems(config, items):
    test_dir = pathlib.PosixPath(__file__).parent / "tests"
    package_tags = {
        test_dir / "replica": pytest.mark.replica,
        test_dir / "integration": pytest.mark.integration,
        test_dir / "interactive": pytest.mark.interactive,
    }

    for item in items:
        test_path = pathlib.PosixPath(item.fspath)

        # Append package based tags
        for package_dir, package_tag in package_tags.items():
            if test_path.is_relative_to(package_dir):
                item.add_marker(package_tag)

        # If the item has no tags (including those added in code), then mark it as unmarked
        if not any(item.iter_markers()):
            item.add_marker(pytest.mark.unmarked)


# Ensure we have the static collected, when running interactive requests
@pytest.fixture(scope="session", autouse=True)
def collect_static_files(request):
    need_static = any(item.get_closest_marker("interactive") for item in request.session.items)
    if need_static:
        call_command("collectstatic", verbosity=0, interactive=False)
