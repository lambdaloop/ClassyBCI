"""Core OpenBCI objects for handling connections and samples from the board.
"""
import time
import struct
import serial
import numpy as np

# Custom parameters.
BAUD = 115200  # * 2
STARTUP_TIMEOUT = 3  # seconds; initial timeout
RUN_TIMEOUT = 1  # seconds; timeout to use once running.
READ_INTERVAL_MS = 250


START_BYTE = bytes(0xA0)  # start of data packet
END_BYTE = bytes(0xC0)  # end of data packet

TIMESERIES_LENGTH = 4500
MIN_HISTORY_LENGTH = 4500
MAX_HISTORY_LENGTH = 65000

# Hardware/Calibration parameters. ###########
gain_fac = 24.0
full_scale_V = 4.5 / gain_fac
correction_factor = 2.0  # Need to revisit why we need this factor, but based on
                        # physical measurements, it is necessary
creare_volts_per_count = full_scale_V / (2.0 ** 24) * correction_factor
creare_volts_per_FS = creare_volts_per_count * 2 ** (24 - 1)  # per full scale: +/- 1.0
#############################

SAMPLE_RATE = 250.0  # Hz
CHANNELS = 8

class OpenBCIBoard(object):
  """Handle a connection to an OpenBCI board.

  Args:
    port: The port to connect to.
    baud: The baud of the serial connection.
  """

  
  def __init__(self, port, baud):
    self.ser = serial.Serial(port, baud)
    self.dump_registry_data()
    self.streaming = False
    self.should_stream = False
    self.channels = 8
    self.i_sample = 0
    
  def dump_registry_data(self):
    """Dump all the debug data until we get to a line with something
    about streaming data.
    """
    line = ''
    while 'begin streaming data' not in line:
      line = self.ser.readline()

  def start_streaming(self, callback):
    """Start handling streaming data from the board. Call a provided callback
    for every single sample that is processed.

    Args:
      callback: A callback function that will receive a single argument of the
          OpenBCISample object captured.
    """
    if not self.streaming:
      # Send an 'x' to the board to tell it to start streaming us text.
      self.ser.write('x')
      # Dump the first line that says "Arduino: Starting..."
      self.ser.readline()

    self.should_stream = True
    
    while self.should_stream:
      data = self.ser.readline()
      if self.should_stream:
        sample = OpenBCISample(data)
      if self.should_stream:
        callback(sample)


  def _read_serial_binary(self, max_bytes_to_skip=3000):
        """
        Returns (and waits if necessary) for the next binary packet. The
        packet is returned as an array [sample_index, data1, data2, ... datan].

        RAISES
        ------
        RuntimeError : if it has to skip to many bytes.

        serial.SerialTimeoutException : if there isn't enough data to read.
        """
        #global i_sample
        def read(n):
            val = self.ser.read(n)
            # print bytes(val),
            return val

        n_int_32 = self.channels + 1

        # Look for end of packet.
        for i in xrange(max_bytes_to_skip):
            val = read(1)
            if not val:
                if not self.ser.inWaiting():
                    print('Device appears to be stalled. Restarting...')
                    self.ser.write('b\n')  # restart if it's stopped...
                    time.sleep(.100)
                    continue
            # self.serial_port.write('b\n') , s , x
            # self.serial_port.inWaiting()
            if bytes(struct.unpack('B', val)[0]) == END_BYTE:
                # Look for the beginning of the packet, which should be next
                val = read(1)
                if bytes(struct.unpack('B', val)[0]) == START_BYTE:
                    if i > 0:
                        print("Had to skip %d bytes before finding stop/start bytes." % i)
                    # Read the number of bytes
                    val = read(1)
                    n_bytes = struct.unpack('B', val)[0]
                    if n_bytes == n_int_32 * 4:
                        # Read the rest of the packet.
                        val = read(4)
                        sample_index = struct.unpack('i', val)[0]
#                         if sample_index != 0:
#                             logging.warn("WARNING: sample_index should be zero, but sample_index == %d" % sample_index)
                        # NOTE: using i_sample, a surrogate sample count.
                        t_value = self.i_sample / float(SAMPLE_RATE)  # sample_index / float(SAMPLE_RATE)
                        self.i_sample += 1
                        val = read(4 * (n_int_32 - 1))
                        data = struct.unpack('i' * (n_int_32 - 1), val)
                        data = np.array(data) / (2. ** (24 - 1));  # make so full scale is +/- 1.0
                        # should set missing data to np.NAN here, maybe by testing for zeros..
                        # data[np.logical_not(self.channel_array)] = np.NAN  # set deactivated channels to NAN.
                        data[data == 0] = np.NAN
                        #data = data * creare_volts_per_FS * 1.0e6
                        # print data
                        return np.concatenate([[t_value], data])  # A list [sample_index, data1, data2, ... datan]
                    elif n_bytes > 0:
                        print "Warning: Message length is the wrong size! %d should be %d" % (n_bytes, n_int_32 * 4)
                        # Clear the buffer of those bytes.
                        _ = read(n_bytes)
                    else:
                        raise ValueError("Warning: Message length is the wrong size! %d should be %d" % (n_bytes, n_int_32 * 4))
        raise RuntimeError("Maximum number of bytes skipped looking for binary packet (%d)" % max_bytes_to_skip)

        
  def disconnect(self):
    self.ser.close()

class OpenBCISample(object):
  """Object encapulsating a single sample from the OpenBCI board."""

  def __init__(self, data):
    parts = data.rstrip().split(', ')
    self.id = parts[0]
    self.channels = []
    for c in xrange(1, len(parts) - 1):
      self.channels.append(int(parts[c]))
    # This is fucking bullshit but I have to strip the comma from the last
    # sample because the board is returning a comma... wat?
    self.channels.append(int(parts[len(parts) - 1][:-1]))

