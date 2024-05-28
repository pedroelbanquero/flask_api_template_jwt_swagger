sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-dev build-essential
sudo apt-get install -y mongodb
sudo systemctl start mongodb
sudo systemctl enable mongodb
sudo apt-get install -y libsodium-dev
sudo apt-get install -y libffi-dev libssl-dev
sudo apt-get install -y curl
./mongo.sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


