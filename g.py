import io,sys
p=sys.argv[1] if len(sys.argv)>1 else 'coffee_breaker.py'
k=sys.argv[2]
a=int(sys.argv[3]) if len(sys.argv)>3 else 0
b=int(sys.argv[4]) if len(sys.argv)>4 else 10**9
L=io.open(p,encoding='utf-8',errors='replace').read().split('\n')
h=[i+1 for i,s in enumerate(L) if k in s and a<=i+1<=b]
print(len(h),','.join(map(str,h[:12])))
