import csv, json, math, sys, glob, collections
M=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'research/backtest/matrix.json'))
P,OV=M['P'],M['ov']; W=set(P)
rows=[];seen=set()
for f in ['lck','lpl','lec_lcs','intl_minor']:
    for r in csv.DictReader(open(f'research/backtest/{f}.csv')):
        try: sa,sb=int(r['score_a']),int(r['score_b'])
        except: continue
        a,b=r['team_a'].strip(),r['team_b'].strip()
        key=(r['date'],r['event'],tuple(sorted([a,b])),tuple(sorted([sa,sb])))
        if key in seen: continue
        seen.add(key); rows.append(dict(r,a=a,b=b,sa=sa,sb=sb,bo=int(r['best_of'] or 1)))
lg=lambda p:math.log(p/(1-p)); sg=lambda x:1/(1+math.exp(-x))
# Worlds team strengths on a logit scale, fitted to the sim matrix (least squares on logits)
ids=sorted(W); s={i:0.0 for i in ids}
for it in range(3000):
    for i in ids:
        g=sum((s[i]-s[j])-lg(min(.995,max(.005,P[i][j]))) for j in ids if j!=i)
        s[i]-=0.01*g
# non-Worlds team strengths: max likelihood on their games, Worlds teams held at sim values
others=sorted({x for r in rows for x in (r['a'],r['b'])}-W)
for x in others: s[x]=-1.0
for it in range(400):
    for x in others:
        gr=0;h=0
        for r in rows:
            if x not in (r['a'],r['b']): continue
            o=r['b'] if r['a']==x else r['a']; wx,wo=(r['sa'],r['sb']) if r['a']==x else (r['sb'],r['sa'])
            p=sg(s[x]-s[o]); gr+=wx-(wx+wo)*p; h+=(wx+wo)*p*(1-p)
        s[x]+=gr/(h+1e-9)*0.5 - 0.02*s[x]*0   # newton step
def pg(a,b): return P[a][b] if a in W and b in W else sg(s[a]-s[b])
def series(p,bo):
    need=bo//2+1; tot=0
    for k in range(need, bo+1):  # prob a wins in exactly k games
        tot+=math.comb(k-1,need-1)*p**need*(1-p)**(k-need)
    return tot
def evaluate(sel,label):
    G=[];S=[]
    for r in sel:
        p=pg(r['a'],r['b'])
        G+= [(p,1)]*r['sa'] + [(p,0)]*r['sb']
        S.append((series(p,r['bo']),1 if r['sa']>r['sb'] else 0, r))
    if not G: return
    brier=sum((p-y)**2 for p,y in G)/len(G); ll=-sum(math.log(p if y else 1-p) for p,y in G)/len(G)
    acc=sum((p>.5)==(y==1) for p,y in G if p!=.5)/len(G)
    sacc=sum((p>.5)==(y==1) for p,y,_ in S)/len(S); sbr=sum((p-y)**2 for p,y,_ in S)/len(S)
    print(f"\n## {label}: {len(S)} series, {len(G)} games")
    print(f"games: favourite won {acc*100:.0f}% | Brier {brier:.3f} (coin flip 0.250) | log loss {ll:.3f} (coin flip 0.693)")
    print(f"series: favourite won {sacc*100:.0f}% | Brier {sbr:.3f}")
    B=collections.OrderedDict((k,[0,0,0.0]) for k in ['50-60','60-70','70-80','80-90','90+'])
    for p,y in G:
        f=max(p,1-p); won = y if p>=.5 else 1-y
        k='90+' if f>=.9 else '80-90' if f>=.8 else '70-80' if f>=.7 else '60-70' if f>=.6 else '50-60'
        B[k][0]+=1;B[k][1]+=won;B[k][2]+=f
    for k,(n,w,ps) in B.items():
        if n: print(f"  predicted {k}%: {n} games, predicted {ps/n*100:.0f}%, favourite actually won {w/n*100:.0f}%")
    return S
ww=[r for r in rows if r['a'] in W and r['b'] in W]
wo=[r for r in rows if (r['a'] in W)!=(r['b'] in W)]
print("Teams fitted:",len(others),"non-Worlds | rows",len(rows))
S1=evaluate(ww,"Worlds team vs Worlds team (main test)")
intl=[r for r in ww if any(k in r['event'] for k in ['First Stand','MSI','Esports World Cup','Worlds'])]
evaluate(intl,"…of which international events")
evaluate(wo,"Worlds team vs other teams (opponent strength fitted from results)")
# baseline: higher ov wins
G=[(OV[r['a']]-OV[r['b']],r['sa'],r['sb']) for r in ww]
acc=sum(sa if d>0 else sb for d,sa,sb in G if d!=0)/sum(sa+sb for d,sa,sb in G if d!=0)
print(f"\nBaseline 'higher team rating wins each game' (Worlds v Worlds): {acc*100:.0f}%")
# biggest misses
miss=sorted([(abs(p-y),p,y,r) for p,y,r in S1 if (p>.5)!=(y==1)],key=lambda x:-x[0])[:8]
print("\nBiggest series misses:")
for d,p,y,r in miss: print(f"  {r['date']} {r['event']} {r['a']} {r['sa']}-{r['sb']} {r['b']}: model gave {r['a']} {p*100:.0f}%")
json.dump({k:round(v,3) for k,v in s.items()},open('research/backtest/strengths.json','w'))
