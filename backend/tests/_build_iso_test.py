
import pathlib
tests_dir = pathlib.Path(__file__).parent
target = tests_dir / 'test_repos_isolated.py'
content = (tests_dir / '_iso_test_content.py').read_text(encoding='utf-8')
target.write_text(content, encoding='utf-8')
print('Written:', target.stat().st_size, 'bytes')
