load("@rules_python//python:defs.bzl", "py_binary", "py_library")
load("@pip_deps//:requirements.bzl", "requirement")
load("@rules_pkg//:pkg.bzl", "pkg_deb", "pkg_tar")

py_binary(
    name = "switch_heat_mode",
    srcs = ["switch_heat_mode.py"],
    visibility = ["//:__pkg__"],
    deps = [
        "//:config",
        "//:connect",
        requirement("prometheus_client"),
        requirement("libdyson"),
    ],
)
