// Standalone analysis: six upper boxes, 3K, 4K, Yahtzee; all other boxes closed.
#include <array>
#include <vector>
#include <map>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <algorithm>
using namespace std;
struct Hand {array<int,6> c; int n,sum,mx,face; array<int,6> add; vector<int> sub;};
vector<Hand> h; vector<int> full; map<array<int,6>,int> ids;
vector<double> memo(512*64*2,-1); long long solved=0;
void gen(array<int,6>& c,int f,int remain){if(f==5){c[f]=remain; Hand x{};x.c=c;for(int i=0;i<6;i++){x.n+=c[i];x.sum+=(i+1)*c[i];if(c[i]>x.mx){x.mx=c[i];x.face=i;}}ids[c]=h.size();h.push_back(x);return;}for(int j=0;j<=remain;j++){c[f]=j;gen(c,f+1,remain-j);}}
double V(int mask,int upper,bool live);
pair<double,int> choice(int mask,int upper,bool live,int rid,int cat){
 auto &r=h[rid]; bool extra=live&&r.mx==5; int upperbit=1<<r.face;
 if(!(mask&256)&&r.mx==5){if(mask&upperbit){if(cat!=r.face)return {-1e100,0};}else if(mask&448){if(cat<6)return {-1e100,0};}}
 int score=cat<6?(cat+1)*r.c[cat] : cat==6?(r.mx>=3?r.sum:0):cat==7?(r.mx>=4?r.sum:0):(r.mx==5?50:0);
 int bonus=extra?100:0;bool nextlive=live||(cat==8&&score==50);
 return {score+bonus+V(mask^(1<<cat),min(63,upper+(cat<6?score:0)),nextlive),score+bonus};
}
void expect(array<double,462>& e){for(int i=209;i>=0;i--){double s=0;for(int f=0;f<6;f++)s+=e[h[i].add[f]];e[i]=s/6;}}
double V(int mask,int upper,bool live){if(!mask)return upper==63?35:0;int key=(mask*64+upper)*2+live; if(memo[key]>=0)return memo[key];array<double,462> e{};
 for(int rid:full){double best=-1e100;for(int c=0;c<9;c++)if(mask&(1<<c))best=max(best,choice(mask,upper,live,rid,c).first);e[rid]=best;}
 expect(e);
 for(int roll=0;roll<2;roll++){array<double,252> b{};int i=0;for(int rid:full){double best=-1e100;for(int sub:h[rid].sub)best=max(best,e[sub]);b[i++]=best;}i=0;for(int rid:full)e[rid]=b[i++];expect(e);}
 solved++;return memo[key]=e[0];}
int main(){array<int,6> c{};for(int n=0;n<=5;n++)gen(c,0,n);if(h.size()!=462)return 2;for(int i=0;i<462;i++){if(h[i].n<5){for(int f=0;f<6;f++){auto a=h[i].c;a[f]++;h[i].add[f]=ids[a];}}else{full.push_back(i);for(int j=0;j<462;j++){bool legal=true;for(int f=0;f<6;f++)if(h[j].c[f]>h[i].c[f])legal=false;if(legal)h[i].sub.push_back(j);}}}
 ifstream states("states.txt");int key;
 ofstream out("terminal_choices.csv");out<<"state,dice,category,score_now,total_value,future_value\n"<<setprecision(16);
 while(states>>key){int globalmask=key&8191;int mask=(globalmask&255)|((globalmask&(1<<11))?256:0);int upper=(key>>13)&63;bool live=key&(1<<19);
 for(int rid:full){string dice;for(int f=0;f<6;f++)dice+=string(h[rid].c[f],char('1'+f));for(int cat=0;cat<9;cat++)if(mask&(1<<cat)){auto q=choice(mask,upper,live,rid,cat);out<<key<<","<<dice<<","<<cat<<","<<q.second<<","<<q.first<<","<<q.first-q.second<<"\n";}}
 }
 cerr<<"states solved "<<solved<<"\n";
}
