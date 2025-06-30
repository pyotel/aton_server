ARG MOSQUITTO_VERSION
FROM eclipse-mosquitto:${MOSQUITTO_VERSION}

COPY mosquitto.conf /opt/mosquitto.conf
COPY mosquitto-entrypoint.sh /

ENTRYPOINT ["sh", "mosquitto-entrypoint.sh"]

CMD ["/usr/sbin/mosquitto", "-c", "/opt/mosquitto.conf"]
