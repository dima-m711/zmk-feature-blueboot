/*
 * Copyright (c) 2026 te9no
 *
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT zmk_behavior_blueboot

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/logging/log.h>
#include <zephyr/retention/retention.h>
#include <zephyr/sys/reboot.h>

#include <drivers/behavior.h>
#include <zmk/behavior.h>

LOG_MODULE_DECLARE(zmk, CONFIG_ZMK_LOG_LEVEL);

#if DT_HAS_COMPAT_STATUS_OKAY(DT_DRV_COMPAT)

#if DT_HAS_CHOSEN(zmk_magic_boot_mode)
static const struct device *const magic_retention =
    DEVICE_DT_GET(DT_CHOSEN(zmk_magic_boot_mode));
#endif

static int on_keymap_binding_pressed(struct zmk_behavior_binding *binding,
                                     struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);

#if DT_HAS_CHOSEN(zmk_magic_boot_mode)
    if (!device_is_ready(magic_retention)) {
        LOG_ERR("Blueboot retention device is not ready");
        return ZMK_BEHAVIOR_OPAQUE;
    }

    const uint8_t ota_magic = CONFIG_ZMK_BLUEBOOT_MAGIC;
    int ret = retention_write(magic_retention, 0, &ota_magic, sizeof(ota_magic));
    if (ret < 0) {
        LOG_ERR("Failed to request Blueboot mode (%d)", ret);
        return ZMK_BEHAVIOR_OPAQUE;
    }

    LOG_INF("Rebooting into Blueboot mode");
    sys_reboot(SYS_REBOOT_WARM);
#else
    /*
     * ZMK/Zephyr releases before the boot-mode retention API pass the
     * Adafruit GPREGRET value through sys_reboot() on Nordic targets.
     */
    LOG_INF("Rebooting into Blueboot mode");
    sys_reboot(CONFIG_ZMK_BLUEBOOT_MAGIC);
#endif

    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api behavior_blueboot_driver_api = {
    .binding_pressed = on_keymap_binding_pressed,
    .locality = BEHAVIOR_LOCALITY_EVENT_SOURCE,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .get_parameter_metadata = zmk_behavior_get_empty_param_metadata,
#endif
};

#define BLUEBOOT_INST(n)                                                                        \
    BEHAVIOR_DT_INST_DEFINE(n, NULL, NULL, NULL, NULL, POST_KERNEL,                            \
                            CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &behavior_blueboot_driver_api);

DT_INST_FOREACH_STATUS_OKAY(BLUEBOOT_INST)

#endif
