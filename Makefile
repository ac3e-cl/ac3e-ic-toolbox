.PHONY: all print build xserver start start-vnc attach start-raw start-notebook start-devcontainer push pull rm
# Export supplied Make variables without including executable Make syntax from .env.
export
all: print
print:
	@./runtime/start.sh print
build:
	./runtime/start.sh build
xserver:
	@printf '%s\n' 'Use your existing X server and DISPLAY; no global X access is changed.'
start:
	./start_x.sh
start-vnc:
	./start_vnc.sh
start-raw:
	./start_shell.sh
start-notebook:
	./start_jupyter.sh
attach:
	./runtime/start.sh attach
start-devcontainer: pull
	./runtime/start.sh devcontainer
push:
	./runtime/start.sh push
pull:
	./runtime/start.sh pull
rm:
	./runtime/start.sh rm
