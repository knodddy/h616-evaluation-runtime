# U-Boot v2026.10 and TF-A v2.14.0, fetched only for the firmware target.
UBOOT_REV := 5508406582f6f7120dce0c4b3059819a41788db2
TFA_REV := 1d5aa939bc8d3d892e2ed9945fa50e36a1a924cc
FIRMWARE := $(abspath build/firmware)
BL31 := $(FIRMWARE)/tf-a/build/sun50i_h616/release/bl31.bin

$(FIRMWARE)/u-boot/.source: boot/firmware.mk
	git init $(FIRMWARE)/u-boot
	git -C $(FIRMWARE)/u-boot fetch --depth 1 https://github.com/u-boot/u-boot.git $(UBOOT_REV)
	git -C $(FIRMWARE)/u-boot checkout --detach $(UBOOT_REV)
	touch $@

$(FIRMWARE)/tf-a/.source: boot/firmware.mk
	git init $(FIRMWARE)/tf-a
	git -C $(FIRMWARE)/tf-a fetch --depth 1 https://github.com/ARM-software/arm-trusted-firmware.git $(TFA_REV)
	git -C $(FIRMWARE)/tf-a checkout --detach $(TFA_REV)
	touch $@

$(BL31): $(FIRMWARE)/tf-a/.source
	$(MAKE) -C $(FIRMWARE)/tf-a CROSS_COMPILE=$(CROSS_COMPILE) \
		CC=$(CROSS_COMPILE)gcc AS=$(CROSS_COMPILE)gcc LD=$(CROSS_COMPILE)ld \
		AR=$(CROSS_COMPILE)ar OC=$(CROSS_COMPILE)objcopy OD=$(CROSS_COMPILE)objdump \
		PLAT=sun50i_h616 bl31

$(FIRMWARE)/u-boot/.config: $(FIRMWARE)/u-boot/.source boot/h616-eval_defconfig boot/sun50i-h616-eval.dts
	cp boot/h616-eval_defconfig $(FIRMWARE)/u-boot/configs/h616-eval_defconfig
	cp boot/sun50i-h616-eval.dts $(FIRMWARE)/u-boot/dts/upstream/src/arm64/allwinner/
	$(MAKE) -C $(FIRMWARE)/u-boot CROSS_COMPILE=$(CROSS_COMPILE) h616-eval_defconfig

$(FIRMWARE)/u-boot/u-boot-sunxi-with-spl.bin: $(FIRMWARE)/u-boot/.config $(BL31)
	$(MAKE) -C $(FIRMWARE)/u-boot CROSS_COMPILE=$(CROSS_COMPILE) BL31=$(BL31)

# Unpartitioned console-only image; H616 Boot ROM also checks sector 256.
build/u-boot-sd.img: $(FIRMWARE)/u-boot/u-boot-sunxi-with-spl.bin
	test $$(stat -c %s $<) -le $$((4 * 1024 * 1024 - 128 * 1024))
	rm -f $@
	truncate -s 4M $@
	dd if=$< of=$@ bs=1K seek=128 conv=notrunc status=none
