# TODO: build_root() is deprecated since Meson 0.56.0. Port to
# project_build_root() once the version lands in all supported
# releases.
build_dir = meson.build_root()
# TODO: source_root() is deprecated since Meson 0.56.0. Port to
# project_source_root() once the version lands in all supported
# releases.
source_dir = meson.source_root()

test_env = environment()
test_env.set('PYTHONPATH',
  join_paths(build_dir, 'src')
)
test_env.prepend('PATH',
  join_paths(build_dir, 'src')
)
test_env.set('RETRACE_SERVER_CONFIG_PATH',
  join_paths(source_dir, 'src', 'config', 'retrace-server.conf')
)
test_env.set('RETRACE_SERVER_PLUGIN_DIR',
  join_paths(build_dir, 'src', 'plugins')
)
test_env.set('RETRACE_SERVER_TESTING', '1')

test_files = [
  'test_architecture.py',
  'test_backends.py',
  'test_util.py',
]

foreach file: test_files
  configure_file(
    copy: true,
    input: file,
    output: file,
  )
endforeach

pytest_args = []
if get_option('coverage')
  pytest_args += ['--cov=./', '--cov-report=xml']
endif

test('Python unit tests',
  pytest,
  args: pytest_args,
  env: test_env,
)
