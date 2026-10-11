package model

import "net"

func ValidPodCIDR(s string) bool {
	ip, n, e := net.ParseCIDR(s)
	if e != nil || ip.To4() == nil || !ip.IsPrivate() || !ip.Equal(n.IP) {
		return false
	}
	ones, bits := n.Mask.Size()
	return bits == 32 && ones >= 24 && ones <= 28
}
func SubnetsOverlap(a, b string) bool {
	_, x, e := net.ParseCIDR(a)
	if e != nil {
		return false
	}
	_, y, e := net.ParseCIDR(b)
	return e == nil && (x.Contains(y.IP) || y.Contains(x.IP))
}
