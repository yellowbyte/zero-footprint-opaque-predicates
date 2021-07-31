import sys 


from pprint import pprint



file1 = sys.argv[1]  # correct (original)
file2 = sys.argv[2]  # identification from tool (e.g., binsec)

with open(file1, "r") as f:
    file1_content = f.readlines()

with open(file2, "r") as f:
    file2_content = f.readlines()

file1_content = set(int(i.rstrip().rstrip("L"),16) for i in file1_content)
file2_content = set(int(i.rstrip().rstrip("L"),16) for i in file2_content)

# metrics
fn = len(file1_content.difference(file2_content))
fp = len(file2_content.difference(file1_content))
tp = len(file1_content.intersection(file2_content))

print("FN: "+str(fn))  # elements present in file1 and not file2 (i.e., inserted opaque predicates not identified)
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
#pprint([hex(addr) for addr in list(file1_content.difference(file2_content))])
#print("")
print("FP: "+str(fp))  # elements present in file2 and not file1 (i.e., bb misidentified as opaque predicates)
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
#pprint([hex(addr) for addr in list(file2_content.difference(file1_content))])
#print("")
print("TP: "+str(tp))
print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
#pprint([hex(addr) for addr in list(file1_content.intersection(file2_content))])
