from os.path import join
from pathlib import Path
from subprocess import run

import sh

from pythonforandroid.recipe import CythonRecipe
from pythonforandroid.toolchain import current_directory, info, shprint

# get git root
print("Getting audiostream recipe")
git_root = Path(__file__).parent.parent.parent.parent.parent
# audiostream directory
audiostream_dir = git_root / "audiostream"
# get git hash of latest commit
commit_hash = (
    run(["git", "rev-parse", "HEAD"], cwd=audiostream_dir, capture_output=True)
    .stdout.decode()
    .strip()
)
# get remote url of the repository
remote_url = (
    run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=audiostream_dir,
        capture_output=True,
    )
    .stdout.decode()
    .strip()
)
# download zip archive of the repository
run(["curl", "-L", "-o", "audiostream.zip", f"{remote_url}/archive/{commit_hash}.zip"])
# compute its hash
shasum = (
    run(["sha256sum", "audiostream.zip"], capture_output=True)
    .stdout.decode()
    .strip()
    .split(" ")[0]
    .strip()
)
# delete the zip file
run(["rm", "audiostream.zip"])


class AudiostreamRecipe(CythonRecipe):
    # audiostream has no tagged versions; this is the latest commit to master 2020-12-22
    # it includes a fix for the dyload issue on android that was preventing use
    version = commit_hash
    url = "https://github.com/audioseek/audiostream/archive/{version}.zip"
    # sha256sum = shasum
    name = "audiostream"
    depends = ["python3", "sdl2", "pyjnius"]

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        sdl_include = "SDL2"

        env["USE_SDL2"] = "True"
        env["SDL2_INCLUDE_DIR"] = join(
            self.ctx.bootstrap.build_dir, "jni", "SDL", "include"
        )

        env["CFLAGS"] += " -I{jni_path}/{sdl_include}/include".format(
            jni_path=join(self.ctx.bootstrap.build_dir, "jni"), sdl_include=sdl_include
        )

        sdl2_mixer_recipe = self.get_recipe("sdl2_mixer", self.ctx)
        for include_dir in sdl2_mixer_recipe.get_include_dirs(arch):
            env["CFLAGS"] += " -I{include_dir}".format(include_dir=include_dir)

        # NDKPLATFORM is our switch for detecting Android platform, so can't be None
        env["NDKPLATFORM"] = "NOTNONE"
        env["LIBLINK"] = "NOTNONE"  # Hacky fix. Needed by audiostream setup.py
        return env

    def postbuild_arch(self, arch):
        # TODO: This code was copied from pyjnius, but judging by the
        #       audiostream history, it looks like this step might have
        #       happened automatically in the past.
        #       Given the goal of migrating off of recipes, it would
        #       be good to repair or build infrastructure for doing this
        #       automatically, for when including a java class is
        #       the best solution to a problem.
        super().postbuild_arch(arch)
        info("Copying audiostream java files to classes build dir")
        with current_directory(self.get_build_dir(arch.arch)):
            shprint(
                sh.cp,
                "-a",
                join("audiostream", "platform", "android"),
                self.ctx.javaclass_dir,
            )


recipe = AudiostreamRecipe()
