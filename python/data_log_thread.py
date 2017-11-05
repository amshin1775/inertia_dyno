import threading, time, csv, datetime

class data_log_thread(threading.Thread):

	def __init__(self, my_sample_freq, my_thread_timing, my_rpm_res, my_torque_res, my_test_time_res, my_can_data_res, my_data_log_st_res):

		super().__init__(name="data log thread")

		# keep track of when thread it active
		self.active = threading.Event()

		# store passed in parameters
		self.sample_freq = my_sample_freq
		self.thread_timing = my_thread_timing
		self.test_time_res = my_test_time_res
		self.rpm_res = my_rpm_res
		self.torque_res = my_torque_res

		#102917 Added parameter and field in order to use the can_data_r
		#shared resource
		self.can_data_r = my_can_data_res

		#110517 Added parameter and field in order to use the data_log_st_r shared resource
		self.data_log_st_r = my_data_log_st_res

		# sleep the thread every 1 us, effectively updating the test time about that fast
		self.thread_block_period = 1E-6 

	def start(self):

		print(super().getName() + " is starting.")
		self.active.set()
		super().start()


	def run(self):

		#102917 Create a file with the format of YYYY-MM-DD HH-MM-SS.Ms
		f = open(str(datetime.datetime.now()), 'w')

		#102917 Created csv_writer for use in writing to the data csv file
		csv_writer = csv.writer(f)

		# 110517 Added header to csv file
		csv_writer.writerow(['Time Elapsed', 'RPM', 'Torque', 'Pulse Width?', 'Engine RPM', 'Engine Advance', 'Manifold Air Pressure', 'Manifold Air Temperature', 'Coolant Temperature', 'Throttle Position Sensor', 'Air-Fuel Ratio', 'Air Correction?', 'Warm Correction?', 'Throttle Acceleration', 'Total Correction?', 'tpsFuelCutId', 'coldAdvDegId', 'tpsDotId', 'mapDotId', 'rpmDotId'])

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

				# 110517 Added check for data_log_st_r to see if we need to log
				if data_log_st_r.get() == True:

					# write to CSV
					#102917 Seconds since start + RPM + Torque + CAN
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
