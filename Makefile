PKGS := raylib \
		jim \
		nob \
		arena \
		flag \
		ffmpeg_renderer \
		defer \
		stb \
		ffi \
		dill \
		mill \
		pjim \
		mongoose \
		pll \
		jim-module \
		raylib-module

all: create_gitignore $(PKGS:%=%.tar.gz)

create_gitignore:
	echo "" > .gitignore

%.tar.gz: %
	tar -czf $@ ./$<
	echo $@ >> .gitignore	

.PHONY: all $(PKGS)

clean:
	rm -f $(PKGS:=.tar.gz)
