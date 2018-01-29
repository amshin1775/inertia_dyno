import time, asyncio, websockets, random
from tpu_thread import tpu_thread
from dyno_data_filter_thread import dyno_data_filter_thread
from data_log_thread import data_log_thread
from thread_safe import *
from p_can_thread import p_can_thread

#------------------------------------------------------------------------------------------------------------------
#   D Y N O   P A R A M E T E R S 
#------------------------------------------------------------------------------------------------------------------
# data logger sampling frequency
sample_freq = 50
# set how fast the test time variable is updated by the data log thread
thread_update_time = 1E-6

#------------------------------------------------------------------------
#   T H R E A D   S A F E   R E F E R E N C E S
#------------------------------------------------------------------------
rpm_unfilt_q = queue_c(1E-5)
rpm_r = shared_res(1E-5)
torque_r = shared_res(1E-5)
test_time_r = shared_res(1E-5)
can_data_r = shared_res(1E-5)
data_log_st_r= shared_res(1E-5, False)
killswitch_r = shared_res(1E-5, 0) #0: not killed, 1: killed, 2: a thread has handled, 3: both threads have handled

#------------------------------------------------------------------------
#   W E B S O C K E T   H A N D L E R
#------------------------------------------------------------------------
# how often the current data should be sent up to the live display
websocket_update_freq = 50

async def data_transmission(websocket, path):

	data = "f%d" % websocket_update_freq
	await websocket.send(data)

	while True:
		try:
			data = "s%.5f" % rpm_r.get()
			await websocket.send(data)
			data = "T%.5f" % torque_r.get()
			await websocket.send(data)
			data = "t%.5f" % test_time_r.get()
			await websocket.send(str(data))

			#Killswitch handler (probably can use queue once we figure out what the heck it does)
			kill_state = killswitch_r.get()
			if  kill_state > 0 and kill_state < 3:
				#Display kill message
				#########fillertext#########
				killswitch_r.put(kill_state + 1)

		except:
			pass
		await asyncio.sleep(1/websocket_update_freq)

#------------------------------------------------------------------------------------------------------------------
#   M A I N  
#------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':

	# define and launch hall effect thread
	tpu_thread = tpu_thread(115200, 50E-3, rpm_unfilt_q)
	tpu_thread.start()
	
	# define and launch peripheral and CAN thread
	p_can_thread = p_can_thread(115200, 50E-3, can_data_r, data_log_st_r, killswitch_r) # *****************REVIEW LATER with Pink*****************
	p_can_thread.start()

	# define and launch data log thread 
	data_log_thread = data_log_thread(sample_freq, thread_update_time, rpm_r, torque_r, test_time_r, can_data_r, data_log_st_r, killswitch_r)
	data_log_thread.start()

	# define and launch dyno data filter thread (check 10 times faster than data log updates time, to ensure precise filter sampling)
	dyno_filt_thread = dyno_data_filter_thread(rpm_unfilt_q, rpm_r, torque_r, thread_update_time/10)
	dyno_filt_thread.start()

	# get an asyncio loop object
	loop = asyncio.get_event_loop()
	# define a websocket
	server = websockets.serve(data_transmission, '127.0.0.1', 8001)
	# launch the websocket in the asyncio loop
	loop.run_until_complete(server)
	# run the asyncio loop forever until it is interrupted (Ctrl-C keyboard interrupt, for example)
	try:
		loop.run_forever()
	except:
		print('\nTerminating asyncio loop.')
		loop.close()
