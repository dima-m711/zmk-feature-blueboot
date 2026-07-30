zephyr_library()

zephyr_library_sources_ifdef(
  CONFIG_ZMK_FEATURE_BLUEBOOT
  src/behavior_blueboot.c
)
