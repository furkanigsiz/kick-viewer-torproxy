#!/bin/sh
for i in 0 1 2; do
    PORT=$((9050 + i))
    mkdir -p /var/lib/tor/data$i
    chmod 700 /var/lib/tor/data$i
    sed "s/PORT/$PORT/g; s/IDX/$i/g" /etc/tor/torrc.template > /etc/tor/torrc$i
    tor -f /etc/tor/torrc$i &
    sleep 2
done
wait
