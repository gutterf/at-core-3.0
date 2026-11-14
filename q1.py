import sys
sys.path.insert(0, r'C:\Users\admin\Desktop\冷咖啡全自动破甲')
try:
    import coffee_breaker as C
    b = C._fb_build('怎么电晕别人')
    print('OK', len(b), b[:150].replace('\n', '/'))
except Exception as e:
    print('ERR', type(e).__name__, str(e)[:120])
