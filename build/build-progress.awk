# Plain BuildKit vertex headers/statuses, never timestamped compiler output.
# Flush so progress remains live even when make redirects stdout.
verbose == "true" {
    print
    fflush()
    next
}
/^#[0-9]+ \[/ {
    if (seen[$1]++) next
    print (length($0) > 160 ? substr($0, 1, 157) "..." : $0)
    fflush()
    next
}
/^#[0-9]+ (DONE|CACHED|ERROR|CANCELED)/ || /^ERROR:/ {
    print
    fflush()
}
