zephyr_library()

# External Zephyr libraries do not inherit the app target's private includes.
zephyr_library_include_directories(${APPLICATION_SOURCE_DIR}/include)

zephyr_library_sources_ifdef(
  CONFIG_ZMK_FEATURE_BLUEBOOT
  src/behavior_blueboot.c
)
