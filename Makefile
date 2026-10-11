.PHONY: test vet build deb clean

test:
	go test -race -count=1 ./...
vet:
	go vet ./...
build:
	mkdir -p build
	CGO_ENABLED=0 go build -trimpath -o build/werft ./cmd/werft
deb:
	bash scripts/build-deb.sh
clean:
	rm -rf build dist

source-check:
	python3 scripts/check-public-source.py
	python3 -m unittest discover -s tests/release -v

qualification:
	python3 scripts/check-release.py --commit "$$(git rev-parse HEAD)"
