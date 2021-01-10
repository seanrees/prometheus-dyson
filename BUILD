load("@rules_python//python:defs.bzl", "py_binary", "py_library")
load("@pip_deps//:requirements.bzl", "requirement")
load("@rules_pkg//:pkg.bzl", "pkg_tar", "pkg_deb")

py_library(
    name = "metrics",
    srcs = ["metrics.py"],
    deps = [
        requirement("libpurecool"),
        requirement("prometheus_client")
    ],
)

py_test(
    name = "metrics_test",
    srcs = ["metrics_test.py"],
    deps = [
        ":metrics",
        requirement("libpurecool"),
        requirement("prometheus_client")
    ],
)
py_binary(
    name = "main",
    srcs = ["main.py"],
    deps = [
        ":metrics",
        requirement("libpurecool"),
        requirement("prometheus_client")
    ],
)

pkg_tar(
    name = "deb-bin",
    package_dir = "/opt/prometheus-dyson/bin",
    # This depends on --build_python_zip.
    srcs = [":main"],
    mode = "0755",
)

pkg_tar(
    name = "deb-config-sample",
    package_dir = "/etc/prometheus-dyson",
    srcs = ["config-sample.ini"],
    mode = "0644",
)

pkg_tar(
    name = "deb-default",
    package_dir = "/etc/default",
    srcs = ["debian/prometheus-dyson"],
    mode = "0644",
    strip_prefix = "debian/"
)

pkg_tar(
    name = "deb-service",
    package_dir = "/lib/systemd/system",
    srcs = ["debian/prometheus-dyson.service"],
    mode = "0644",
    strip_prefix = "debian/"
)

pkg_tar(
    name = "debian-data",
    deps = [
      ":deb-bin",
      ":deb-config-sample",
      ":deb-default",
      ":deb-service",
    ]
)

pkg_deb(
    name = "main-deb",
    # libpurecool has native deps.
    architecture = "amd64",
    built_using = "bazel",
    data = ":debian-data",
    depends = [
        "python3",
    ],
    prerm = "debian/prerm",
    postrm = "debian/postrm",
    description_file = "debian/description",
    maintainer = "Sean Rees <sean at erifax.org>",
    package = "prometheus-dyson",
    version = "0.0.2",
)
