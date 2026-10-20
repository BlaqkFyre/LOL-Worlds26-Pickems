/* Worlds 2026 Pick'Em: static data. Sources listed in the page footer and README. */
/* [name, [attr1,attr2,attr3], [[champ,games,wr%],...], kda, note] */
const TEAMS=[
 {id:"GEN",name:"Gen.G",reg:"LCK #1",p:[
  ["Kiin",[94,90,97],[["Ambessa",17,82],["Sion",12,92],["Rumble",10,70]],3.93,"Highest LCK playoff gold diff at 15 (+354); 5.1 KDA in playoffs"],
  ["Canyon",[93,96,95],[["Pantheon",17,71],["Xin Zhao",16,56],["Vi",15,67]],5.16,"Lee Sin 12-1 in 2026 (Sheep); likely target-banned"],
  ["Chovy",[99,93,96],[["Ryze",19,74],["Galio",16,81],["Anivia",14,79]],null,"Led LCK playoff mids in KDA (7.28), CS/min and gold/min"],
  ["Ruler",[92,93,98],[["Jhin",18,83],["Ezreal",16,69],["Yunara",15,67]],5.11,"5.43 KDA, 806 DPM, 72% win rate in LCK"],
  ["Duro",[85,88,97],[["Seraphine",17,71],["Bard",14,79],["Karma",12,67]],5.02,"5.15 KDA, 72.6% win rate; stable over flashy"]]},
 {id:"HLE",name:"Hanwha Life",reg:"LCK #2 · MSI champion",p:[
  ["Zeus",[97,95,90],[["Gnar",19,68],["Ambessa",15,67],["Jayce",14,93]],3.21,"MSI Finals MVP; Strafe's #1 top laner"],
  ["Kanavi",[96,88,90],[["Jarvan IV",26,50],["Vi",23,74],["Pantheon",15,67]],3.11,"Most deaths of any LCK jungler in summer; high-risk aggression"],
  ["Zeka",[94,89,92],[["Ryze",19,68],["Ahri",16,63],["Aurora",16,63]],5.52,"+333 gold at 15, 19 solo kills"],
  ["Gumayusi",[90,90,93],[["Ziggs",20,75],["Jhin",20,45],["Caitlyn",17,88]],3.73,"3.82 KDA in LCK; three-time world champion"],
  ["Delight",[96,92,84],[["Bard",19,74],["Seraphine",14,71],["Alistar",14,71]],4.05,"Most deaths in LCK playoffs; elite engage"]]},
 {id:"T1",name:"T1",reg:"LCK #3 · defending champion",p:[
  ["Doran",[87,85,74],[["Jayce",21,81],["Ambessa",19,53],["Gnar",15,53]],2.80,"Most solo kills among LCK playoff tops (9); volatile"],
  ["Oner",[91,85,86],[["Vi",24,92],["Xin Zhao",24,75],["Jarvan IV",17,59]],3.70,"Most solo kills among LCK junglers in summer (6)"],
  ["Faker",[82,92,87],[["Ryze",21,57],["Anivia",17,71],["Orianna",16,63]],3.19,"Negative gold/XP at 15; still decisive mid-late"],
  ["Peyz",[95,97,90],[["Jhin",17,65],["Lucian",15,67],["Caitlyn",14,71]],4.46,"Hotspawn's #1 ADC; 6 kills a game in LCK playoffs"],
  ["Keria",[96,97,95],[["Milio",16,69],["Bard",14,71],["Camille",13,62]],4.51,"4.89 KDA, 76.3% KP in LCK"]]},
 {id:"DK",name:"Dplus KIA",reg:"LCK #4 · EWC champion",p:[
  ["Siwoo",[88,85,76],[["Jayce",21,43],["K'Sante",19,74],["Gnar",16,81]],2.05,"Most deaths among LCK playoff tops"],
  ["Lucid",[84,81,82],[["Jarvan IV",31,71],["Xin Zhao",25,56],["Vi",16,44]],3.28,"EWC champion; still building a world-class record"],
  ["ShowMaker",[90,89,90],[["Viktor",17,65],["Ryze",15,67],["Annie",13,69]],3.59,"Best form since 2020–21; 25% win rate on assassins"],
  ["Smash",[87,90,84],[["Lucian",16,63],["Yunara",16,50],["Ezreal",16,38]],4.39,"Most CS among LCK playoff ADCs; 28.5% damage share"],
  ["Career",[89,90,80],[["Lulu",19,53],["Bard",16,63],["Karma",14,71]],4.11,"2nd in LCK for KP and first-blood %; first Worlds"]]},
 {id:"BLG",name:"Bilibili Gaming",reg:"LPL #2 · First Stand champion",p:[
  ["Bin",[91,90,80],[["Gnar",23,83],["Sion",18,72],["Renekton",16,56]],3.71,"Questionable summer; criticised Kai'Sa pick in LPL final"],
  ["Xun",[92,88,87],[["Pantheon",26,73],["Jarvan IV",24,75],["Xin Zhao",19,74]],4.82,"Strong synergy with ON; 4.82 KDA"],
  ["Knight",[90,97,98],[["Ryze",22,86],["Orianna",15,87],["Syndra",14,79]],6.49,"Strafe's #1 mid; 715.7 DPM, 5.5 KDA in LPL"],
  ["Viper",[89,92,93],[["Ezreal",28,79],["Ashe",18,94],["Yunara",16,63]],5.44,"4.68 KDA, 69% win rate; highest KDA in LPL final"],
  ["ON",[95,92,92],[["Bard",27,63],["Alistar",21,67],["Seraphine",19,95]],3.91,"72.5% win rate over 109 games; poor LPL final"]]},
 {id:"AL",name:"Anyone's Legend",reg:"LPL #1",p:[
  ["Breathe",[86,89,86],[["Gnar",18,56],["K'Sante",11,64],["Ambessa",11,45]],3.08,"Revived career; LPL Split 3 champion"],
  ["Tarzan",[95,93,92],[["Naafiri",20,60],["Pantheon",20,60],["Jarvan IV",16,63]],4.68,"Strafe's #1 jungler; LPL final MVP"],
  ["Shanks",[84,85,86],[["Ryze",23,65],["Azir",18,67],["Cassiopeia",15,40]],4.13,"648.9 DPM; off last year's peak"],
  ["Hope",[82,82,92],[["Varus",21,81],["Ezreal",18,56],["Corki",17,59]],4.49,"4.91 KDA in Split 3; 2.3 deaths a game in LPL final"],
  ["Kael",[89,92,90],[["Neeko",16,75],["Bard",15,67],["Seraphine",15,40]],4.30,"4.63 KDA, 75.4% KP; elite duo with Tarzan"]]},
 {id:"TES",name:"Top Esports",reg:"LPL #3",p:[
  ["369",[78,82,76],[["Ambessa",6,50],["Rumble",4,75],["K'Sante",4,50]],2.44,"Stand-in for ZUIAN (visa); very few 2026 games"],
  ["Tian",[83,81,81],[["Jarvan IV",15,67],["Vi",12,75],["Lee Sin",12,58]],3.40,"75% win rate on Lee Sin in summer (Hotspawn)"],
  ["Creme",[83,82,87],[["Azir",18,39],["Ryze",17,47],["Ahri",14,79]],3.87,"744.3 DPM; quieter last split"],
  ["JackeyLove",[84,83,80],[["Ezreal",14,79],["Ashe",14,71],["Jhin",12,33]],3.47,"Lowest damage share among LPL-final ADCs; inconsistent"],
  ["Zhuo",[78,81,85],[["Lulu",15,40],["Milio",13,46],["Seraphine",12,58]],4.40,"Led TES in KDA, lowest death share"]]},
 {id:"IG",name:"Invictus Gaming",reg:"LPL #4",p:[
  ["TheShy",[86,87,77],[["Rumble",6,67],["Gnar",4,75],["Yorick",4,75]],2.47,"Returned mid-year; struggled recently"],
  ["Wei",[84,79,80],[["Xin Zhao",17,35],["Jarvan IV",16,69],["Nocturne",13,62]],null,"Played 11 champions in summer; Pantheon 1-11 in 2026"],
  ["Rookie",[82,84,85],[["Syndra",10,50],["Ryze",10,40],["Orianna",8,75]],3.90,"766.8 DPM, 5.0 KDA, +172 gold at 15 in summer"],
  ["JiaQi",[79,80,76],[["Yunara",18,67],["Jhin",14,21],["Ashe",13,69]],2.79,"First international event"],
  ["Meiko",[85,90,84],[["Lulu",15,67],["Seraphine",12,58],["Bard",10,60]],3.75,"77%+ KP, 2nd among LPL supports"]]},
 {id:"G2",name:"G2 Esports",reg:"LEC #1",p:[
  ["BrokenBlade",[78,88,84],[["K'Sante",21,71],["Rumble",13,62],["Kled",11,91]],3.15,"Weakest laning numbers of LEC playoff teams; strong late"],
  ["SkewMond",[86,83,83],[["Xin Zhao",22,73],["Jarvan IV",16,75],["Pantheon",14,71]],4.63,"69.8% KP, +338 XP at 15, 4.68 KDA (Sheep)"],
  ["Caps",[85,90,87],[["Ahri",15,60],["Orianna",13,92],["Ryze",11,55]],4.31,"7.07 KDA in LEC playoffs (Strafe)"],
  ["Hans Sama",[84,82,92],[["Yunara",19,63],["Ashe",14,86],["Ezreal",14,57]],4.27,"Highest KDA in LEC playoffs (6.7); question is carrying"],
  ["Labrov",[88,86,88],[["Lulu",19,68],["Bard",12,75],["Seraphine",11,82]],3.32,"LEC Finals MVP; 13 champions in summer"]]},
 {id:"MKOI",name:"Movistar KOI",reg:"LEC #2",p:[
  ["Myrwn",[75,77,74],[["Rumble",21,62],["Ambessa",13,62],["Renekton",9,67]],2.57,"Rough year; needs to step up"],
  ["Elyoya",[79,80,79],[["Pantheon",14,79],["Vi",14,64],["Jarvan IV",14,43]],4.47,"Team captain"],
  ["Jojopyun",[86,83,82],[["Ryze",15,33],["Azir",14,36],["Anivia",11,73]],3.40,"+209 gold at 15, 14 solo kills; team's standout"],
  ["Supa",[74,75,76],[["Ezreal",18,50],["Yunara",13,54],["Ashe",12,75]],4.07,"Disappointing year (Hotspawn)"],
  ["Alvaro",[77,81,80],[["Neeko",13,69],["Seraphine",13,62],["Lulu",12,50]],3.63,"Strong end to LEC playoffs"]]},
 {id:"KC",name:"Karmine Corp",reg:"LEC #3 · play-in winner",p:[
  ["Canna",[80,81,78],[["Rumble",32,72],["Gnar",18,78],["Sion",14,57]],3.13,"Struggled in LEC playoffs"],
  ["Yike",[78,78,78],[["Vi",25,84],["Wukong",16,63],["Jarvan IV",15,80]],3.69,"Vi 21-4 in 2026"],
  ["kyeahoo",[78,79,77],[["Azir",17,71],["Ryze",15,67],["Orianna",13,54]],4.00,"Valued for his role in KC's system"],
  ["Caliste",[83,84,77],[["Ezreal",20,50],["Caitlyn",15,73],["Ashe",15,67]],5.18,"Aggressive hyper-carry style; first Worlds"],
  ["Busio",[91,84,78],[["Seraphine",18,67],["Bard",17,59],["Nami",15,53]],3.95,"1st in LEC first-blood participation (45.2%)"]]},
 {id:"TL",name:"Team Liquid",reg:"LCS #1",p:[
  ["Morgan",[78,79,80],[["Renekton",13,62],["Rumble",13,54],["Gnar",12,50]],3.49,"Solid at MSI"],
  ["Josedeodo",[82,79,79],[["Jarvan IV",14,50],["Pantheon",12,83],["Xin Zhao",11,45]],5.22,"LCS Finals MVP; Lee Sin 88.9% (Sheep)"],
  ["Quid",[80,80,81],[["Ryze",18,83],["Orianna",13,69],["Yone",9,67]],4.33,"Helped TL to the LCS title"],
  ["Yeon",[80,80,82],[["Lucian",12,83],["Ashe",12,83],["Xayah",12,75]],4.51,""],
  ["CoreJJ",[78,84,90],[["Rakan",13,69],["Seraphine",11,82],["Rell",11,64]],5.14,"Best KDA in the LCS, 1st in assists"]]},
 {id:"LYON",name:"LYON",reg:"LCS #2",p:[
  ["Dhokla",[76,78,80],[["Gnar",17,59],["Rumble",16,69],["K'Sante",12,50]],2.65,"Solid at MSI"],
  ["Inspired",[88,84,83],[["Xin Zhao",16,69],["Wukong",15,67],["Nocturne",12,50]],4.17,"Best Western jungler for many; low kill participation"],
  ["Saint",[80,79,79],[["Ryze",15,67],["Viktor",12,67],["Sylas",10,70]],3.73,"4.3 KDA, 18 solo kills; inconsistent lately"],
  ["Berserker",[87,86,84],[["Yunara",18,67],["Ezreal",15,73],["Lucian",14,64]],5.11,"LCS Summer MVP"],
  ["Isles",[81,81,82],[["Lulu",18,67],["Nautilus",13,46],["Milio",11,64]],4.45,"31% counter-pick rate"]]},
 {id:"TSW",name:"Team Secret Whales",reg:"LCP #1",p:[
  ["Pun",[70,73,68],[["Renekton",11,55],["Olaf",9,78],["Jax",9,67]],2.92,"Weak LCP form"],
  ["Hizto",[77,72,73],[["Jarvan IV",20,60],["Xin Zhao",18,67],["Naafiri",14,43]],5.02,"LCP Split 2 and 3 MVP; Vi 91.7% (Sheep)"],
  ["Dire",[73,74,73],[["Ryze",18,72],["Ahri",15,87],["Aurora",15,67]],4.59,"LCP stats discounted for league strength"],
  ["Eddie",[74,75,77],[["Ezreal",15,53],["Yunara",14,71],["Kai'Sa",12,92]],5.62,"LCP stats discounted for league strength"],
  ["Bie",[76,75,78],[["Nautilus",21,76],["Karma",12,58],["Bard",11,73]],5.68,"Off-meta picks (Skarner, LeBlanc)"]]},
 {id:"CFO",name:"CTBC Flying Oyster",reg:"LCP #2",p:[
  ["Rest",[73,74,72],[["Rumble",17,53],["Renekton",12,33],["Gnar",8,50]],2.84,""],
  ["Shad0w",[74,75,74],[["Jarvan IV",12,25],["Pantheon",11,73],["Wukong",10,30]],3.27,"Second straight Worlds"],
  ["Pout",[74,73,76],[["Akali",11,55],["Aurora",8,25],["Orianna",6,50]],3.52,"Carries on comfort picks"],
  ["Doggo",[76,77,75],[["Lucian",13,54],["Ezreal",10,50],["Kai'Sa",10,40]],3.44,""],
  ["Kino",[74,70,70],[["Nautilus",9,67],["Lulu",8,38],["Milio",7,57]],3.04,"Aggressive engage player"]]},
 {id:"LOS",name:"LOS",reg:"CBLOL #1",p:[
  ["Zest",[76,72,71],[["Rumble",13,77],["Jayce",11,55]],3.35,"+497 gold at 15 in CBLOL playoffs; 9.2 CS/min"],
  ["Curse",[71,70,70],[["Pantheon",16,69],["Xin Zhao",13,38],["Vi",12,58]],3.67,"Worlds debut; high DPM, low kill participation"],
  ["Feisty",[72,71,72],[["Ryze",21,71],["Orianna",14,57],["Taliyah",12,67]],4.36,"5.2 KDA, 75% KP in CBLOL playoffs"],
  ["Duduhh",[70,70,71],[["Corki",12,75],["Ezreal",12,50],["Lucian",10,50]],3.8,"18 years old; 80% win rate in Split 2"],
  ["Ackerman",[75,74,74],[["Alistar",13,77],["Bard",11,55],["Neeko",10,40]],6.27,"6.6 KDA in CBLOL playoffs (3rd); Rakan 8-0"]]}
];
/* Worlds 2026 pick+ban presence on 26.20 (NerfPlz). Ryze: most-picked across latest pro games. */
const PRES={"Nocturne":95,"Seraphine":68,"Olaf":63,"Vi":55,"Ezreal":50,"K'Sante":50,"Lee Sin":46,"Akali":46,"Cassiopeia":45,"Rumble":41,"Renata Glasc":41,"Caitlyn":41,"Jarvan IV":41,"Syndra":37,"Viktor":37,"Jax":37,"Locke":37,"Pantheon":37,"Lulu":36,"Lucian":32,"Jayce":32,"Gnar":32,"Orianna":32,"Sylas":32,"Yone":32,"Maokai":32,"Skarner":28,"Camille":27,"Rakan":27,"Vayne":27,"Milio":23,"Ambessa":23,"Naafiri":23,"Xayah":23,"Zaahen":18};
const RECENT={"Ryze":"most-picked champion in the latest pro games (26%)"};
/* meta tier list: [champ, role, picked%, banned%, record/wr, note] from NerfPlz Worlds 2026 (26.20) */
const CH=[
 ["Nocturne","JGL",0,95,"never picked","Banned in 65% of recent pro games too"],
 ["Seraphine","SUP",18,50,"75%",""],
 ["Olaf","TOP",18,45,"100%",""],
 ["Vi","JGL",23,32,"100% (5-0)","Banned in 51% of recent pro games"],
 ["Ezreal","ADC",23,27,"60%","Among most-picked in recent pro games"],
 ["K'Sante","TOP",23,27,"0%","Nerfed on 26.20"],
 ["Lee Sin","JGL",23,23,"60%",""],
 ["Akali","MID",14,32,"33%","Banned in 37% of recent pro games"],
 ["Cassiopeia","MID",18,27,"100%","Nerfed on 26.20; banned in 82% of recent pro games"],
 ["Rumble","TOP",27,14,"50%","Most-played champion by different players at Worlds"],
 ["Renata Glasc","SUP",9,32,"0-2",""],
 ["Caitlyn","ADC",5,36,"0-1",""],
 ["Jarvan IV","JGL",27,14,"67%","Most-picked champion at Worlds so far"],
 ["Ryze","MID",null,null,"","Most-picked champion in the latest pro games (26%); not in the play-in table"],
 ["Syndra","MID",23,14,"40%",""],
 ["Viktor","MID",23,14,"80%",""],
 ["Jax","TOP",14,23,"33%",""],
 ["Locke","MID",14,23,"33%",""],
 ["Pantheon","JGL",5,32,"0-1",""],
 ["Lulu","SUP",27,9,"50%",""],
 ["Lucian","ADC",27,5,"33%","Buffed on 26.20"],
 ["Jayce","TOP",18,14,"75%",""],
 ["Gnar","TOP",9,23,"2-0",""],
 ["Orianna","MID",9,23,"1-1","Banned in 37% of recent pro games"],
 ["Sylas","MID",9,23,"0-2",""],
 ["Yone","MID",9,23,"0-2",""],
 ["Maokai","JGL",5,27,"0-1",""],
 ["Skarner","JGL",5,23,"1-0",""],
 ["Camille","TOP",18,9,"25%","Also played as support"],
 ["Rakan","SUP",18,9,"50%",""],
 ["Vayne","ADC",0,27,"never picked","Buffed on 26.20"],
 ["Milio","SUP",23,0,"40%",""],
 ["Ambessa","TOP",18,5,"25%","Nerfed on 26.20"],
 ["Naafiri","JGL",18,5,"25%",""],
 ["Xayah","ADC",18,5,"50%",""],
 ["Zaahen","TOP",18,0,"75%",""]
];
/* Bot duos, patch 26.20 solo queue, metabot.gg (145,320 ranked games): [adc, sup, winrate, lift, games] */
const DUOS=[["Xayah","Milio",62.6,7.9,147],["Xayah","Alistar",58.2,6.9,110],["Kai'Sa","Bard",54.4,6.8,136],["Kai'Sa","Renata Glasc",56.9,6.1,102],["Kog'Maw","Lulu",59.9,6.0,302],["Kai'Sa","Alistar",54.8,5.3,290],
 ["Ashe","Seraphine",53.2,3.7,1138],["Ashe","Lulu",52.2,3.4,274],["Ashe","Milio",54.4,2.5,282],["Caitlyn","Alistar",53.1,2.3,294],["Ezreal","Milio",50.8,1.8,177],["Jhin","Milio",54.9,1.3,335],["Yunara","Lulu",51.0,1.0,739],["Yunara","Alistar",50.8,0.9,124],["Jhin","Bard",49.1,0.7,226],
 ["Xayah","Rakan",50.8,-0.3,907],["Ezreal","Seraphine",46.2,-0.3,507],["Yunara","Seraphine",50.4,-0.3,379],["Jhin","Seraphine",50.2,-0.8,1039],["Lucian","Milio",51.0,-0.8,510],["Caitlyn","Seraphine",50.1,-1.5,1116],["Lucian","Seraphine",47.6,-1.6,275],
 ["Caitlyn","Bard",45.8,-3.1,249],["Ashe","Alistar",44.7,-3.9,123],["Yunara","Milio",49.0,-4.2,308],["Ezreal","Lulu",38.6,-7.2,140],["Lucian","Lulu",40.3,-8.3,134],["Jhin","Renata Glasc",43.0,-8.6,100],["Jhin","Lulu",39.6,-10.7,227]];
const MSRC_S={"Xayah|Rakan":"52.6% over 111K games","Ashe|Seraphine":"52.1% over 169K games","Kog'Maw|Lulu":"54.0% over 45K games"};
/* METAsrc 26.20 synergy partners for core meta picks: role -> [champ, +change%, games] */
const PARTNERS=[
 ["Jarvan IV","JGL","jarvan",{MID:[["Lissandra",1.7,"11.5K"]],ADC:[["Kog'Maw",2.6,"5.6K"],["Zeri",1.2,"8.4K"],["Sivir",1.0,"9.1K"]],SUP:[["Leona",2.7,"20.5K"],["Milio",1.4,"12.3K"],["Alistar",1.1,"10.1K"]]}],
 ["Vi","JGL","vi",{MID:[["Viktor",1.9,"21.5K"],["Ahri",1.2,"42.4K"],["Yone",1.1,"33.1K"]],ADC:[["Kog'Maw",2.0,"7.5K"],["Xayah",1.6,"16.3K"]],SUP:[["Leona",2.1,"27.6K"],["Rell",1.5,"9.9K"],["Seraphine",1.0,"35.5K"]]}],
 ["Ryze","MID","ryze",{TOP:[["Renekton",2.1,"6.8K"],["Yone",1.1,"14.1K"]],JGL:[["Wukong",2.3,"9.1K"],["Lillia",1.8,"5.5K"]],ADC:[["Xayah",1.5,"6.9K"]],SUP:[["Leona",3.0,"10.8K"],["Alistar",2.0,"5.4K"],["Seraphine",1.8,"13.1K"],["Milio",1.2,"6.5K"]]}],
 ["Seraphine","SUP","seraphine",{JGL:[["Wukong",3.6,"42.6K"],["Lillia",2.1,"29.8K"]],MID:[["Yone",2.0,"82.4K"],["Viktor",1.1,"33.4K"]],ADC:[["Kog'Maw",1.9,"12.1K"],["Ashe",1.5,"169.2K"]]}]
];
/* Worlds 2026 play-in drafts (patch 26.20), as listed by eGamersWorld: [series, game, winner comp, loser comp, winner, loser] */
const COMPS=[
 ["KC vs C9",1,["Rumble","Xin Zhao","Locke","Ezreal","Karma"],["Rumble","Lee Sin","Syndra","Miss Fortune","Nautilus"],"C9","KC"],
 ["KC vs C9",2,["Jayce","Vi","Cassiopeia","Varus","Vel'Koz"],["Camille","Wukong","Akali","Kalista","Renata Glasc"],"KC","C9"],
 ["KC vs C9",3,["Olaf","Jarvan IV","Annie","Jhin","Alistar"],["Kled","Naafiri","Anivia","Lucian","Nami"],"C9","KC"],
 ["KC vs C9",4,["Renekton","Qiyana","Orianna","Xayah","Rakan"],["Zaahen","Sejuani","Sylas","Yunara","Lulu"],"KC","C9"],
 ["KC vs C9",5,["Ambessa","Trundle","Ahri","Kai'Sa","Rell"],["K'Sante","Lillia","Yone","Ziggs","Shen"],"KC","C9"],
 ["KC vs MVK (UB)",1,["Jax","Vi","Syndra","Draven","Nautilus"],["Ambessa","Maokai","K'Sante","Tristana","Lulu"],"KC","MVK"],
 ["KC vs MVK (UB)",2,["Galio","Lee Sin","Ahri","Ashe","Seraphine"],["Twisted Fate","Qiyana","Rumble","Ezreal","Pyke"],"KC","MVK"],
 ["KC vs MVK (UB)",3,["Kennen","Jarvan IV","Viktor","Xayah","Rakan"],["Yorick","Wukong","Kog'Maw","Lucian","Milio"],"KC","MVK"],
 ["MVK vs FURIA",1,["Zaahen","Jarvan IV","Cassiopeia","Ezreal","Lulu"],["Camille","Sejuani","Syndra","Lucian","Milio"],"MVK","FURIA"],
 ["MVK vs FURIA",2,["Gnar","Vi","Kog'Maw","Jhin","Bard"],["Ambessa","Nasus","Viktor","Xayah","Rakan"],"MVK","FURIA"],
 ["MVK vs FURIA",3,["Rumble","Skarner","Twisted Fate","Miss Fortune","Seraphine"],["K'Sante","Jayce","Mel","Ziggs","Leona"],"FURIA","MVK"],
 ["MVK vs FURIA",4,["Olaf","Wukong","Ryze","Corki","Shen"],["Jax","Pantheon","Taliyah","Sivir","Alistar"],"MVK","FURIA"],
 ["KC vs MVK (final)",1,["Jayce","Lee Sin","Cassiopeia","Zeri","Yuumi"],["Yorick","Jarvan IV","Akali","Ashe","Seraphine"],"KC","MVK"],
 ["KC vs MVK (final)",2,["Galio","Qiyana","Ryze","Yunara","Lulu"],["Rumble","Malphite","Hwei","Lucian","Milio"],"KC","MVK"]
];
/* ===== Counters: METAsrc counter pages, ranked solo queue. "s" = this champion wins (its win rate), "w" = this champion loses. ===== */
const CTR_RAW={
"Vi":["JGL","26.20","Rengar 54.6,Qiyana 52.2,Lee Sin 52.1,Kha'Zix 51.6,Hecarim 51.5,Kindred 51.4,Shaco 51.4,Naafiri 51.1","Wukong 46.0,Shyvana 46.2,Amumu 46.9,Cho'Gath 46.9,Lillia 47.5,Briar 47.6,Warwick 47.7,Graves 48.7","vi"],
"Jarvan IV":["JGL","26.20","Rengar 55.6,Locke 54.3,Qiyana 53.4,Quinn 52.7,Ambessa 52.6,Shaco 52.4,Hecarim 52.4,Nunu 52.3","Shyvana 46.7,Zaahen 47.2,Wukong 47.2,Zyra 47.2,Rammus 47.9,Master Yi 48.0,Amumu 48.2,Cho'Gath 48.3","jarvan"],
"Nocturne":["JGL","26.20","Rengar 54.8,Locke 54.4,Qiyana 54.3,Nidalee 54.0,Naafiri 53.3,Zed 52.8,Kindred 52.3,Lee Sin 52.3","Shyvana 44.1,Gwen 44.9,Rammus 45.2,Wukong 45.8,Cho'Gath 46.0,Dr. Mundo 46.0,Bel'Veth 46.4,Sejuani 46.8","nocturne"],
"Lee Sin":["JGL","26.20","Rengar 53.6,Qiyana 51.8,Locke 51.7,Hecarim 51.0,Zed 50.6,Talon 50.5,Nidalee 50.4,Kindred 50.4","Shyvana 44.6,Zaahen 44.7,Rammus 44.8,Cho'Gath 44.8,Warwick 45.3,Briar 45.3,Zyra 45.5,Lillia 45.5","lee-sin"],
"Xin Zhao":["JGL","26.17","Rengar 55,Diana 53,Bel'Veth 52,Master Yi 52,Lee Sin 52,Kha'Zix 51,Talon 51,Hecarim 51","Shyvana 46,Warwick 47,Sylas 47,Wukong 48,Briar 48,Jax 48,Naafiri 49,Vi 49","xin-zhao"],
"Pantheon":["JGL","26.20","Locke 56.2,Rengar 53.7,Hecarim 52.2,Evelynn 51.4,Qiyana 51.4,Lee Sin 51.3,Zed 51.3,Quinn 51.1","Poppy 42.9,Maokai 43.1,Wukong 43.6,Taliyah 43.8,Bel'Veth 44.4,Trundle 44.8,Volibear 44.8,Cho'Gath 45.0","pantheon/counters/jungle#"],
"Wukong":["JGL","","Rengar 59.8,Pantheon 57.2,Qiyana 56.9,Kindred 56.3,Kha'Zix 56.3,Naafiri 55.9,Zed 55.8,Locke 55.8","Lillia 48.1,Cho'Gath 48.2,Zyra 48.9,Amumu 49.1,Zaahen 49.2,Shyvana 49.3,Teemo 49.7,Tryndamere 50.0","wukong"],
"Olaf":["TOP","26.20","Jayce 55,Teemo 53,Yasuo 52,Gangplank 52,Urgot 51,Cho'Gath 51,Mordekaiser 51,Yone 51","Illaoi 45,Trundle 45,Tryndamere 46,Sett 47,Garen 48,Fiora 49,Jax 49,Renekton 49","olaf"],
"K'Sante":["TOP","26.20","Corki 51.7,Skarner 50.9,Jayce 49.8,Akali 49.4,Ryze 48.7,Rumble 48.4,Gragas 48.2,Varus 48.0","Kayle 39.1,Singed 40.0,Illaoi 40.8,Garen 41.1,Yorick 42.6,Aurora 42.7,Urgot 43.3,Shen 43.7","ksante"],
"Rumble":["TOP","26.20","Ryze 54,Aurora 54,Vayne 54,Riven 52,Varus 52,Wukong 52,K'Sante 52,Skarner 51","Yone 43,Sett 44,Mordekaiser 46,Teemo 46,Garen 46,Aatrox 47,Darius 48,Malphite 49","rumble"],
"Jax":["TOP","26.20","Kalista 57.3,Irelia 55.8,Volibear 55.4,Gwen 53.8,Varus 53.7,Udyr 53.6,Corki 53.4,Yone 53.2","Illaoi 43.2,Singed 44.2,Dr. Mundo 44.5,Garen 44.5,Malphite 46.2,Poppy 46.3,Quinn 46.6,Cho'Gath 46.6","jax"],
"Jayce":["TOP","26.20","Corki 55.5,Skarner 55.1,Cassiopeia 53.9,Udyr 52.5,Vayne 51.2,Varus 51.1,Gnar 51.0,Riven 50.9","Maokai 41.8,Zac 41.9,Malphite 42.1,Kled 42.2,Dr. Mundo 42.5,Quinn 43.0,Irelia 43.2,Ornn 43.4","jayce"],
"Gnar":["TOP","26.20","Ryze 55.7,K'Sante 54.3,Varus 53.5,Corki 53.2,Maokai 52.4,Poppy 52.3,Volibear 51.9,Skarner 51.9","Malphite 43.3,Ornn 44.3,Zac 44.7,Irelia 45.0,Wukong 45.5,Yorick 45.5,Teemo 45.8,Nasus 45.8","gnar"],
"Ambessa":["TOP","26.20","K'Sante 53,Vladimir 52,Akali 52,Rumble 52,Varus 52,Dr. Mundo 51,Vayne 51,Cho'Gath 51","Renekton 45,Garen 46,Teemo 46,Malphite 46,Volibear 47,Sett 47,Mordekaiser 47,Jax 49","ambessa"],
"Renekton":["TOP","26.20","Riven 57.3,Cassiopeia 55.8,Yasuo 55.7,Skarner 55.0,Ambessa 54.8,K'Sante 54.2,Udyr 54.1,Akali 54.0","Illaoi 43.3,Teemo 45.7,Dr. Mundo 46.3,Garen 47.3,Shen 47.4,Kayle 47.4,Mordekaiser 47.5,Quinn 47.9","renekton"],
"Ryze":["MID","26.17","Corki 56.9,Riven 56.4,Smolder 55.1,Sion 52.3,Jayce 52.1,Orianna 52.1,Vex 51.9,Kennen 51.7","Kayle 43.0,Aurelion Sol 43.1,Syndra 43.3,Swain 43.7,Veigar 43.8,Malzahar 43.9,Vel'Koz 44.2,Ziggs 44.5","ryze"],
"Akali":["MID","","Corki 53.3,Locke 52.6,Azir 52.6,Irelia 51.9,Orianna 51.7,Cassiopeia 51.6,Mel 51.0,Qiyana 50.4","Heimerdinger 42.9,Veigar 43.5,Swain 43.9,Kennen 43.9,Malzahar 44.5,Vex 45.0,Pantheon 45.6,Galio 45.6","akali"],
"Cassiopeia":["MID","26.20","Corki 55.6,Riven 53.9,Ryze 52.8,Azir 52.0,Sylas 50.5,Kassadin 50.2,Neeko 50.2","Heimerdinger 39.6,Sion 40.7,Xerath 40.8,Vel'Koz 41.2,Gwen 42.2,Malzahar 42.7,Veigar 42.9,Brand 43.1","cassiopeia"],
"Syndra":["MID","26.20","Azir 56,Mel 56,Orianna 55,Qiyana 52,Akali 52,Lissandra 52,Zoe 52,Vex 52","Fizz 45,Ekko 46,Xerath 47,Katarina 47,Diana 48,Yasuo 48,Locke 48,Irelia 49","syndra"],
"Viktor":["MID","26.20","Lissandra 54,Zed 53,Yasuo 53,Katarina 52,Sylas 52,LeBlanc 51,Malzahar 51,Akali 51","Gwen 46,Xerath 47,Ekko 49,Kog'Maw 49,Kassadin 49","viktor"],
"Orianna":["MID","26.19","Smolder 54,Cassiopeia 53,Riven 52,Mel 51,Ryze 51,Taliyah 51,Gangplank 51,Azir 50","Syndra 44,Yone 45,Viktor 46,Yasuo 46,Malzahar 46,Ahri 46,Sylas 47,Zed 47","orianna"],
"Azir":["MID","26.19","Gangplank 52.2,Mel 51.5,Riven 51.4,Ryze 51.0,Kayle 50.8,Kennen 50.6,Akshan 50.2,Smolder 50.2","Xerath 41.7,Nasus 42.9,Ekko 43.0,Ziggs 43.7,Gragas 43.8,Viktor 43.9,Swain 44.1,Hwei 44.1","azir"],
"Ahri":["MID","26.20","Corki 57.8,Azir 55.8,Cassiopeia 55.4,Jayce 54.6,Gragas 54.1,Orianna 53.9,Ryze 53.8,Qiyana 53.7","Heimerdinger 47.0,Veigar 48.1,Naafiri 48.2,Yasuo 48.3,Xerath 48.7,Ekko 48.7,Lux 48.8,Malzahar 48.9","ahri"],
"Ezreal":["ADC","26.19","Cassiopeia 50.8,Mel 49.5,Varus 49.1,Corki 48.8,Caitlyn 47.9,Lucian 47.9,Draven 47.7,Miss Fortune 47.2","Katarina 42.6,Karthus 43.5,Aurelion Sol 43.6,Yasuo 43.7,Kog'Maw 43.8,Swain 44.1,Sivir 44.4,Zeri 44.9","ezreal"],
"Caitlyn":["ADC","26.20","Cassiopeia 53.4,Varus 52.6,Ezreal 52.0,Corki 51.6,Draven 51.4,Yunara 51.4,Lucian 51.2,Kalista 51.2","Veigar 46.0,Katarina 46.0,Swain 46.3,Hwei 46.7,Yasuo 46.8,Ziggs 47.2,Nilah 47.6,Aurelion Sol 47.6","caitlyn"],
"Lucian":["ADC","","Ezreal 53.2,Mel 51.7,Varus 50.9,Corki 50.9,Cassiopeia 50.1,Draven 49.9,Yunara 49.9","Veigar 45.2,Swain 45.5,Katarina 46.0,Kog'Maw 46.0,Smolder 46.1,Aurelion Sol 46.9,Jinx 47.0,Hwei 47.1","lucian"],
"Xayah":["ADC","","Katarina 55.2,Nilah 55.0,Ezreal 54.1,Kalista 54.0,Varus 53.9,Kai'Sa 53.4,Samira 53.3,Lucian 53.1","Ziggs 46.6,Smolder 47.3,Veigar 47.5,Hwei 47.6,Jinx 47.7,Kog'Maw 48.2,Swain 48.3,Aurelion Sol 49.0","xayah"],
"Ashe":["ADC","","Varus 52.9,Ezreal 52.8,Lucian 52.6,Kalista 52.1,Mel 51.9,Corki 51.8,Draven 51.6,Vayne 51.4","Karthus 42.5,Aurelion Sol 43.9,Swain 45.9,Brand 46.2,Katarina 46.4,Seraphine 47.0,Kog'Maw 47.3,Twitch 47.4","ashe"],
"Jhin":["ADC","","Ezreal 54,Mel 54,Corki 53,Varus 52,Lucian 52,Draven 52,Caitlyn 51,Ziggs 51","Yasuo 47,Twitch 48,Smolder 48,Jinx 48,Kai'Sa 48,Xayah 49,Tristana 49,Sivir 49","jhin"],
"Yunara":["ADC","26.20","Kalista 52.8,Ezreal 52.7,Cassiopeia 52.6,Mel 52.3,Kai'Sa 51.5,Vayne 51.5,Varus 51.3,Samira 51.2","Swain 45.7,Kog'Maw 46.3,Nilah 46.5,Veigar 46.9,Aurelion Sol 47.0,Viktor 47.2,Twitch 47.3,Hwei 47.4","yunara"],
"Seraphine":["SUP","","Camille 53.9,Mel 53.8,Rakan 53.0,Veigar 52.5,Skarner 52.3,Neeko 52.1,Galio 52.0,Malphite 51.9","Nidalee 45.8,Amumu 45.9,Sion 46.7,Milio 47.4,Hwei 47.6,Teemo 47.8,Sona 47.8,Ziggs 48.2","seraphine"],
"Lulu":["SUP","26.20","Camille 58.2,Mel 56.5,Skarner 55.2,Ziggs 54.8,Sion 54.2,Ivern 54.1,Malphite 53.9,Shaco 53.7","Amumu 45.5,Braum 47.1,Leona 47.2,Blitzcrank 47.8,Thresh 47.9,Vel'Koz 48.3,Sona 48.5,Annie 48.5","lulu"],
"Milio":["SUP","26.17","Ivern 65.0,Skarner 61.3,Annie 60.4,Neeko 57.0,Ashe 56.5,Camille 56.3,Pantheon 55.3,Zoe 55.3","Braum 47.5,Nidalee 47.6,Nami 48.3,Blitzcrank 48.5,Sona 48.8,Zilean 49.7,Senna 49.9,Thresh 50.0","milio"],
"Rakan":["SUP","26.17","Blitzcrank 55,Pyke 54,Braum 54,Karma 54,Nautilus 53,Yuumi 53,Pantheon 53,Lulu 52","Zyra 45,Seraphine 47,Leona 47,Alistar 48,Senna 48,Nami 48,Janna 49,Poppy 49","rakan"],
"Bard":["SUP","","Mel 55,Ashe 54,Skarner 53,Veigar 53,Zoe 53,Ziggs 52,Camille 52","Thresh 47,Leona 47,Nautilus 47,Blitzcrank 48,Seraphine 48,Nami 48,Lulu 48,Lux 49","bard"],
"Nautilus":["SUP","26.20","Mel 56.7,Ashe 56.5,Skarner 56.4,Ivern 55.7,Camille 55.4,Yuumi 55.2,Zoe 54.2,Pyke 53.7","Taric 42.5,Braum 45.2,Rell 45.3,Leona 45.5,Renata Glasc 46.3,Swain 46.6,Alistar 46.7,Morgana 47.8","nautilus"],
"Alistar":["SUP","26.17","Camille 58,Yuumi 54,Pyke 53,Pantheon 53,Braum 52,Rakan 52,Nautilus 52,Blitzcrank 52","Senna 46,Brand 46,Swain 47,Soraka 47,Poppy 48,Zyra 48,Karma 49,Seraphine 49","alistar"]
};
