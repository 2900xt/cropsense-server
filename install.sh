cp ./cropsense-server.service /etc/systemd/cropsense-server.service
systemctl daemon-reload
systemctl enable cropsense-server.service
systemctl start cropsense-server.service
