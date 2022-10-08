echo "Stopping Stream\n"
sudo /home/pi/Desktop/UCTRONICS_Smart_Robot_Car_RaspberryPi-master/mjpg-streamer.sh stop 
echo "Taking snapshot\n"
raspistill -o cam.jpg  
echo "Restarting stream\n"
sudo /home/pi/Desktop/UCTRONICS_Smart_Robot_Car_RaspberryPi-master/mjpg-streamer.sh restart