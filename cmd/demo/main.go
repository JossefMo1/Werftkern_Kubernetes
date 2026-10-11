// A static, non-root, read-only-rootfs workload included as a local image.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"
)

func main() {
	port := flag.Int("port", 8080, "HTTP port")
	flag.Parse()
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		w.Write([]byte("ready\n"))
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		host, _ := os.Hostname()
		json.NewEncoder(w).Encode(map[string]string{"product": "Werftkern", "version": "0.2.0-dev.3", "hostname": host, "message": "Echte Anwendung, ohne Kubernetes gestartet."})
	})
	server := &http.Server{Addr: ":" + strconv.Itoa(*port), Handler: mux, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 10 * time.Second}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	go func() {
		<-ctx.Done()
		s, c := context.WithTimeout(context.Background(), 5*time.Second)
		defer c()
		server.Shutdown(s)
	}()
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		os.Exit(1)
	}
}
