load("@rules_python//python:defs.bzl", "py_binary", "py_library")
load("@pip//:requirements.bzl", "requirement")
load("@rules_pkg//:pkg.bzl", "pkg_deb", "pkg_tar")

py_library(
    name = "account",
    srcs = ["account.py"],
    deps = [
        requirement("libdyson"),
    ],
)

py_library(
    name = "config",
    srcs = ["config.py"],
)

py_test(
    name = "config_test",
    srcs = ["config_test.py"],
    deps = [
        ":config",
    ],
)

py_library(
    name = "metrics",
    srcs = ["metrics.py"],
    deps = [
        requirement("libdyson"),
        requirement("prometheus_client"),
    ],
)

py_test(
    name = "metrics_test",
    srcs = ["metrics_test.py"],
    deps = [
        ":metrics",
        requirement("libdyson"),
        requirement("prometheus_client"),
    ],
)

py_binary(
    name = "main",
    srcs = ["main.py"],
    deps = [
        ":account",
        ":config",
        ":metrics",
        requirement("prometheus_client"),
        requirement("libdyson"),
    ],
)

pkg_tar(
    name = "deb-bin",
    # This depends on --build_python_zip.
    srcs = [":main"],
    mode = "0755",
    package_dir = "/opt/prometheus-dyson/bin",
)

pkg_tar(
    name = "deb-config-sample",
    srcs = ["config-sample.ini"],
    mode = "0644",
    package_dir = "/etc/prometheus-dyson",
)

pkg_tar(
    name = "deb-default",
    srcs = ["debian/prometheus-dyson"],
    mode = "0644",
    package_dir = "/etc/default",
    strip_prefix = "/debian",
)

pkg_tar(
    name = "deb-service",
    srcs = ["debian/prometheus-dyson.service"],
    mode = "0644",
    package_dir = "/lib/systemd/system",
    strip_prefix = "/debian",
)

pkg_tar(
    name = "debian-data",
    deps = [
        ":deb-bin",
        ":deb-config-sample",
        ":deb-default",
        ":deb-service",
    ],
)

pkg_deb(
    name = "main-deb",
    # libdyson includes native deps.
    architecture = "amd64",
    built_using = "bazel",
    data = ":debian-data",
    depends = [
        "python3",
    ],
    description_file = "debian/description",
    maintainer = "Sean Rees <sean at erifax.org>",
    package = "prometheus-dyson",
    postrm = "debian/postrm",
    prerm = "debian/prerm",
    version = "0.2.1",
)
