load("@rules_python//python:defs.bzl", "py_binary", "py_library")
load("@pip//:requirements.bzl", "requirement")
load("@rules_pkg//:pkg.bzl", "pkg_deb", "pkg_tar")

py_binary(
    name = "switch_heat_mode",
    srcs = ["switch_heat_mode.py"],
    deps = [
        "//:config",
        "//:connect",
        requirement("prometheus_client"),
        requirement("libdyson"),
    ],
)
