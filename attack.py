import requests
import gmpy2
import sys
import math
import json
import statistics
import prime

n = 1024
R = 2**(n//2)


SERVER_URL = "http://6857rsa.csail.mit.edu:8080"
TEAM = "ashwang_agrinman_jfuchs" 


#
#   Dependency Notes:
#       This file requires python3 and the gmp library. It also requires the pip
#       module gmpy2.
#
#       First check google for instructions on how to install python3 and gmp
#       for your operating system. They are available with apt-get on Linux and
#       brew on mac.
#
#       Next make sure pip is installed (using python3 not python):
#           https://pip.pypa.io/en/stable/installing/
#
#       Finally install gmpy2
#           python3 -m pip install gmpy2
#
#       If you are using windows, make sure you have Python3.2 or Python3.3
#           installed, then run the appropriate installer from
#           https://pypi.python.org/pypi/gmpy2 to install gmpy2.
#
#       Feel free to post on piazza for assistance!
#

#
#   RSA Server API
#   POST /decrypt
#       json request body
#           team: String, comma-separated list of team member kerberos names (or
#               a practice team name previously generated by the server)
#           ciphertext: String, hex-encoded
#           no_n: bool, optional, if true the server omits the modulus in the response
#               setting this will save some network bandwidth if you already
#               know the modulus for this team strings's key
#       json response body
#           modulus: String, hex-encoded, present if no_n was not true
#           time: integer, units of time the decryption took (use this, not the
#               real time the response takes to arrive)
#
#   POST /guess
#       json request body
#           team: String
#           q: String, hex-encoded, the smaller of (p, q)
#       json response body
#           correct: bool, whether the guess is correct
#
#   GET /gen_practice
#       no request body
#       json response body
#           team: String, a random team string generated by the server
#           p: String, hex-encoded, the larger of the two secret primes
#           q: String, hex-encoded, the smaller of the two secret primes
#

def main():
    #   first make a dummy request to find the public modulus for our team
    initial_request = {"team": TEAM, "ciphertext": "00"*(n//8)}
    r = requests.post(SERVER_URL + "/decrypt", data=json.dumps(initial_request))
    try:
        N = int(r.json()["modulus"], 16)
    except:
        print(r.text)
        sys.exit(1)

    #   compute R^{-1}_N
    Rinv = gmpy2.invert(R, N)

    #   Start with a "guess" of 0, and analyze the zero-one gap, updating our
    #   guess each time. Repeat this for the (512-16) most significant bits of q
    g = 0
    for i in range(512-16):
        gap = compute_gap(g, i, Rinv, 50, N) #50 used to be 512
        #   based on gap, decide whether bit (512 - i) is 0 or 1, and
        #   update g accordingly
        if gap < 500: # large gap indicates bit i is a 1
            g += 2**(511-i)
        # print(hex(g))
    # brute-force last 16 bits
    for i in range(2**16):
        q = g + i
        if prime.isMillerRabinPrime(q):
            if prime.isMillerRabinPrime(N/q):    #   TODO: check if this is a valid q - see if it's a factor of N
                if N/q < q:
                    submit_guess(N/q)
                else:
                    submit_guess(q)

#   compute the gap for a given guess `g` (assuming the top `i` bits are
#   correct)
def compute_gap(g, i, Rinv, n, N):
    #   TODO: compute `g_hi`, `u_g`, and `u_{g_hi}` as in [BB05] Section 3, take
    #   average time over neighborhoods (n = 50 is a good starting point) for
    #   `u_g` and `u_{g_hi}`, and compute the gap
    zeroTimes = []
    oneTimes = []
    for val in range(n): # search over neighborhoods
        g_hi = g+2**(511-i)
        u_g = (g*Rinv) % N
        u_ghi = (g_hi*Rinv) % N
        t0 = time_decrypt(u_g)
        t1 = time_decrypt(u_ghi)
        zeroTimes.append(t0)
        oneTimes.append(t1)
        g += 1
    gap = abs(statistics.mean(zeroTimes) - statistics.mean(oneTimes))
    return gap

#   hex-encode a ciphertext and send it to the server for decryption
#   returns the simulated time the decryption took
def time_decrypt(ctxt):
    padded_ctxt = ctxt_to_padded_hex_string(ctxt, n)
    req = {"team": TEAM, "ciphertext": padded_ctxt, "no_n": True}
    r = requests.post(SERVER_URL + "/decrypt", data=json.dumps(req))
    try:
        return r.json()["time"]
    except:
        print(r.text)

#   converts a gmpy integer into a hex string front-zero padded to n bits
def ctxt_to_padded_hex_string(ctxt, n):
    h = ctxt.digits(16)
    h = "0"*max(n//4 - len(h), 0) + h
    return h

#   requests a random practice key from the server
def gen_practice_key():
    r = requests.get(SERVER_URL + "/gen_practice")
    try:
        json = r.json()
        return {"team": json["team"], "p": int(json["p"], 16), "q": int(json["q"], 16)}
    except:
        print(r.text)
        sys.exit(1)

#   hex-encodes q and sends it to the server, printing the result
def submit_guess(q):
    #   convert q to hex and remove '0x' at beginning
    data = {"team": TEAM, "q": hex(q)[2:-1]}
    r = requests.post(SERVER_URL + "/guess", data=json.dumps(data))
    print(r.text)

if __name__ == "__main__":
    main()
    # print gen_practice_key()
