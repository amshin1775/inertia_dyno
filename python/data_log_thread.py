import threading, time, csv, datetime

class data_log_thread(threading.Thread):

	def __init__(self, my_sample_freq, my_thread_timing, my_rpm_res, my_torque_res, my_test_time_res, my_can_data_res, my_data_log_st_res, my_killswitch_r):

		super().__init__(name="data log thread")

		# keep track of when thread it active
		self.active = threading.Event()

		# store passed in parameters
		self.sample_freq = my_sample_freq
		self.thread_timing = my_thread_timing
		self.test_time_res = my_test_time_res
		self.rpm_res = my_rpm_res
		self.torque_res = my_torque_res
		self.can_data_r = my_can_data_res
		self.data_log_st_r = my_data_log_st_res
		self.killswitch_r = my_killswitch_r

		# sleep the thread every 1 us, effectively updating the test time about that fast
		self.thread_block_period = 1E-6 

	def start(self):

		print(super().getName() + " is starting.")
		self.active.set()
		super().start()


	def run(self):

		#Create a file with the format of YYYY-MM-DD HH-MM-SS.Ms in logs
		f = open("logs/" + str(datetime.datetime.now()) + ".csv", 'w+')

		#Create csv_writer and add header
		csv_writer = csv.writer(f)
		csv_writer.writerow(['Time Elapsed', 'Dyno RPM', 'Torque', 'Pulse Width?', 'Engine RPM', 'Engine Advance', 'Manifold Air Pressure', 'Manifold Air Temperature', 'Coolant Temperature', 'Throttle Position Sensor', 'Air-Fuel Ratio', 'Air Correction?', 'Warm Correction?', 'Throttle Acceleration', 'Total Correction?', 'tpsFuelCutId', 'coldAdvDegId', 'tpsDotId', 'mapDotId', 'rpmDotId'])

		# time variables
		init_test_time = time.time()
		curr_test_time = 0
		last_test_time = 0

		while self.active.isSet():

			# update the test time
			curr_test_time = time.time()-init_test_time
			# update time shared resource (used by data filter to ensure accurate timing)
			self.test_time_res.put(curr_test_time)

			# check if it is time to store data (also grab the most up-to-date data sampling time, updated by the webserver loop)
			if curr_test_time - last_test_time > self.sample_freq:
				# store data

				#If data_log switch is on
				if data_log_st_r.get() == True:

					#Killswitch handler (probably can use queue once we figure out what the heck it does)
					kill_state = killswitch_r.get()
					if  kill_state > 0 and kill_state < 3:
						#Log kill message
						csv_writer.writerow([str('%.3f' % curr_test_time), "Engine killed"])
						killswitch_r.put(kill_state += 1)

					# write to CSV
					csv_writer.writerow([str('%.3f' % curr_test_time), str(rpm_res.get()), str(torque_res.get())] + can_data_r.get())

				# store current test time so that data logging stores at correct rate
				last_test_time = curr_test_time

			# sleep the thread according to timing set above
			time.sleep(self.thread_timing)
				
		f.close()


	def join(self):

		print(super().getName() + " is terminating.")
		self.active.clear()
		super().join(timeout=None)
