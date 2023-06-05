#!/bin/bash

while true; do 
  docker-compose exec mids ab -n 10 -H "Host: user1.comcast.com" http://localhost:5000/ 
  docker-compose exec mids ab -n 10 -H "Host: user1.comcast.com" http://localhost:5000/join_a_guild
  docker-compose exec mids ab -n 10 -H "Host: user1.comcast.com" http://localhost:5000/purchase_a_sword
  docker-compose exec mids ab -n 10 -H "Host: user2.att.com" http://localhost:5000/
  docker-compose exec mids ab -n 10 -H "Host: user2.att.com" http://localhost:5000/join_a_guild
  docker-compose exec mids ab -n 10 -H "Host: user2.att.com" http://localhost:5000/purchase_a_sword
  sleep 10 
done