# Justin Cappos
# July 3rd, 2008
#
# python script to run the repy test cases...   Adapted from a bash script
#
# The types of tests are:
#
#   s_*.py -- The correct result is the same as when run with python
#   e_*.py -- The restricted program produces output on stderr (most likely
#             because it throws an exception)
#   z_*.py -- The restricted program produces no output 
#   n_*.py -- The restricted program produces some output on stdout and no
#             output on stderr
#   b_*.py -- The restricted program produces output on both stderr and stdout
#   u_*.py -- The result of running these programs is undefined.   They are
#             not tested but may be useful as examples
#   l_*.py -- Use circular logging while testing.   These test cases indicate
#             an error by using exitall instead of letting the program 
#             terminate normally...
#
# any of these types of tests may be preceeded by a 'r', which indicates that
# there is a specific restriction file for the test.   For example:
#  re_foo_bar.py -- run the test (expecting an exception) with foo as the 
# restriction file.

import glob
import subprocess
import os
import sys


# what we print at the end...
endput = ''

def run_test(testname):
  global passcount
  global failcount
  if testname.startswith('rs_') or testname.startswith('re_') or \
	testname.startswith('rz_') or testname.startswith('rn_') or \
	testname.startswith('rb_') or testname.startswith('rl_'):

    # must have three parts: r?_restrictionfn_testname.py
    if len(testname.split('_')) != 3:
      raise Exception, "Test name '"+testname+"' does not have 3 parts!"

    # take the 2nd character of the testname 'rs_' -> 's'
    testtype = testname[1]
    restrictfn = testname.split('_')[1]

  elif testname.startswith('s_') or testname.startswith('e_') or \
	testname.startswith('z_') or testname.startswith('n_') or \
	testname.startswith('b_') or testname.startswith('l_'):

    # take the 1st character of the testname 's_' -> 's'
    testtype = testname[0]
    restrictfn = "restrictions.default"
    
  elif testname.startswith('ru_') or testname.startswith('u_'):
    # Do not run undefined tests...
    return

  else:
    raise Exception, "Test name '"+testname+"' of an unknown type!"


  logstream.write("Running test %-50s [" % testname)
  logstream.flush()
  result = do_actual_test(testtype, restrictfn, testname)

  if result:
    passcount = passcount + 1
    logstream.write(" PASS ]\n")
  else:
    failcount = failcount + 1
    logstream.write("FAILED]\n")
  logstream.flush()


def exec_command(command):
# Windows does not like close_fds and we shouldn't need it so...
  p =  subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  # get the output and close
  theout = p.stdout.read()
  p.stdout.close()

  # get the errput and close
  theerr = p.stderr.read()
  p.stderr.close()

  # FreeBSD prints on stdout, when it gets a signal...
  # I want to look at the last line.   it ends in \n, so I use index -2
  if len(theout.split('\n')) > 1 and theout.split('\n')[-2].strip() == 'Terminated':
    # lose the last line
    theout = '\n'.join(theout.split('\n')[:-2])
    
    # however we threw away an extra '\n' if anything remains, let's replace it
    if theout != '':
      theout = theout + '\n'
    


  # everyone but FreeBSD uses stderr
  if theerr.strip() == 'Terminated':
    theerr = ''

  # Windows isn't fond of this either...
  # clean up after the child
#  os.waitpid(p.pid,0)

  return (theout, theerr)
  

def do_actual_test(testtype, restrictionfn, testname):
  global endput

  # match python
  if testtype == 's':
    (pyout, pyerr) = exec_command('python '+testname)
    (testout, testerr) = exec_command('python ../repy.py --simple '+restrictionfn+" "+testname)

    same = True

    if pyout != testout:
      # stdout differs
      endput = endput+testname+"\n"+ "standard out mismatch '"+pyout+"' != '"+testout+"'\n\n"
      same = False
    
    if pyerr != testerr:
      # stderr differs
      endput = endput+testname+"\n"+ "standard err mismatch '"+pyerr+"' != '"+testerr+"'\n\n"
      same = False
    
    return same

  # any out, no err...
  elif testtype == 'n':
    (testout, testerr) = exec_command('python ../repy.py --status foo '+restrictionfn+" "+testname)
    if testout != '' and testerr == '':
      return True
    else:
      endput = endput+testname+"\nout:"+testout+"err:"+ testerr+"\n\n"
      return False

  # any err, no out...
  elif testtype == 'e':
    (testout, testerr) = exec_command('python ../repy.py --status foo '+restrictionfn+" "+testname)
    if testout == '' and testerr != '':
      return True
    else:
      endput = endput+testname+"\nout:"+testout+"err:"+ testerr+"\n\n"
      return False

  # no err, no out...
  elif testtype == 'z':
    (testout, testerr) = exec_command('python ../repy.py --status foo '+restrictionfn+" "+testname)
    if testout == '' and testerr == '':
      return True
    else:
      endput = endput+testname+"\nout:"+testout+"err:"+ testerr+"\n\n"
      return False

  # any err, any out...
  elif testtype == 'b':
    (testout, testerr) = exec_command('python ../repy.py --status foo '+restrictionfn+" "+testname)
    if testout != '' and testerr != '':
      return True
    else:
      endput = endput+testname+"\nout:"+testout+"err:"+ testerr+"\n\n"
      return False

  # no err, no out (logging)...
  elif testtype == 'l':
    # remove any existing log
    try:
      os.remove("experiment.log.old")
      os.remove("experiment.log.new")
    except OSError:
      pass

    # run the experiment
    (testout, testerr) = exec_command('python ../repy.py --logfile experiment.log --status foo '+restrictionfn+" "+testname)

    # first, check to make sure there was no output or error
    if testout == '' and testerr == '':
      try:
        myfo = file("experiment.log.old","r")
        logdata = myfo.read()
        myfo.close()
        if os.path.exists("experiment.log.new"):
          myfo = file("experiment.log.new","r")
          logdata = logdata + myfo.read()
          myfo.close()

        # use only the last 16KB
        logdata = logdata[-16*1024:]

      except:
        endput = endput+testname+"\nCan't read log!\n\n"
        return False
      if "Fail" in logdata:
        endput = endput+testname+"\nString 'Fail' in logdata\n\n"
        return False 
      elif "Success" not in logdata:
        endput = endput+testname+"\nString 'Success' not in logdata\n\n"
        return False 
      else:
        return True

    else:
      endput = endput+testname+"\nHad output or errput! out:"+testout+"err:"+ testerr+"\n\n"
      return False

  else: 
    raise Exception, "Unknown test type '"+str(testout)+"'"


    

def do_oddballtests():
  global passcount
  global failcount
  global endput
  # oddball "stop" tests...
  logstream.write("Running test %-50s [" % "Stop Test 1")
  logstream.flush()

  (testout, testerr) = exec_command('python ../repy.py  --stop nonexist --status foo restrictions.default stop_testsleep.py')
  if testout == '' and testerr == '':
    passcount = passcount + 1
    logstream.write(" PASS ]\n")
  else:
    failcount = failcount + 1
    endput = endput+"Stop Test 1\noutput or errput! out:"+testout+"err:"+ testerr+"\n\n"
    logstream.write("FAILED]\n")



  # oddball "stop" test2...
  logstream.write("Running test %-50s [" % "Stop Test 2")
  logstream.flush()

  (testout, testerr) = exec_command('python ../repy.py  --stop ../repy.py --status foo restrictions.default stop_testsleep.py')
  if testout == '' and testerr != '':
    passcount = passcount + 1
    logstream.write(" PASS ]\n")
  else:
    failcount = failcount + 1
    logstream.write("FAILED]\n")
    endput = endput+"Stop Test 2\noutput or no errput! out:"+testout+"err:"+ testerr+"\n\n"


  # remove the junk file...
  try:
    os.remove("junk_test.out")
  except: 
    pass


  # oddball "stop" test3...
  logstream.write("Running test %-50s [" % "Stop Test 3")
  logstream.flush()

  (testout, testerr) = exec_command('python ../repy.py  --stop junk_test.out --status foo restrictions.default stop_testsleepwrite.py')
  if testout == '' and testerr == '':
    passcount = passcount + 1
    logstream.write(" PASS ]\n")
  else:
    failcount = failcount + 1
    logstream.write("FAILED]\n")
    endput = endput+"Stop Test 3\noutput or errput! out:"+testout+"err:"+ testerr+"\n\n"





  
if len(sys.argv) > 1 and sys.argv[1] == '-q':
  logstream = file("test.output","w")
else:
  logstream = sys.stdout

# these are updated in run_test
passcount=0
failcount=0


# for each test... run it!
for testfile in glob.glob("rs_*.py") + glob.glob("rn_*.py") + \
	glob.glob("rz_*.py") + glob.glob("rb_*.py") + glob.glob("ru_*.py") + \
	glob.glob("re_*.py") + glob.glob("rl_*.py") +glob.glob("s_*.py") + \
	glob.glob("n_*.py") + glob.glob("z_*.py") + glob.glob("b_*.py") + \
	glob.glob("u_*.py") + glob.glob("e_*.py") + glob.glob("l_*.py"):

  run_test(testfile)

do_oddballtests()

print >> logstream, passcount,"tests passed,",failcount,"tests failed"

# only print if there is something to print
if endput:
  print endput