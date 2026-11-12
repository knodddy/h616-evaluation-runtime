{
  description = "H616 bare-metal development and TF boot tooling";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      forEachSystem = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
      ];
    in
    {
      formatter = forEachSystem (system: nixpkgs.legacyPackages.${system}.nixfmt);

      devShells = forEachSystem (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          cross = pkgs.pkgsCross.aarch64-embedded;
        in
        {
          default = pkgs.mkShell {
            CROSS_COMPILE = cross.stdenv.cc.targetPrefix;
            # Host hardening defaults are unsuitable for freestanding firmware.
            hardeningDisable = [ "all" ];

            packages = with pkgs; [
              cross.stdenv.cc
              cross.buildPackages.binutils
              cross.buildPackages.gdb

              git
              gnumake
              pkg-config
              bison
              flex
              swig
              bc
              which
              perl

              clang-tools
              nixfmt

              dtc
              ubootTools
              # Required by upstream U-Boot's image builder.
              (python3.withPackages (ps: [
                ps.setuptools
                ps.pyelftools
                ps.libfdt
              ]))

              genimage
              dosfstools
              mtools
              util-linux
              coreutils
              file

              picocom
              lrzsz
              sunxi-tools
              usbutils
            ];

            buildInputs = with pkgs; [
              openssl
              ncurses
            ];
          };
        }
      );
    };
}
