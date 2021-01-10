# Copyright (c) 2021 nosyn00b <nosyn00b@gmail.com>
# see MIT License and REDAME.md
# This plugin was originally derived from and inspired by the Indiegala Plugin
# https://github.com/burnhamup/galaxy-integration-indiegala
# praise Chris Burnham for that https://github.com/burnhamup
# The original plugin needed deep changes because the react usage on Fanatical site made impossible to scrape games 
# getting them from pure HTML as happens with Indiegala
# Also many other changes to the logic were needed to make all this to work.
# The behaviour of this plugin is now different in so many ways from the original one
# that can really be considered a totally new one :-). 

import json
import os
import logging
from pathlib import Path
import sys
import re
import json
import asyncio
import urllib.parse

from fanatical_configuration import *
from lzstring import lzstring
from datetime import datetime, timedelta

from typing import Optional
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.consts import Platform, LicenseType
from galaxy.api.types import NextStep, Authentication, Game, LicenseInfo
from galaxy.api.errors import AuthenticationRequired
from http_client import HTTPClient

with open(Path(__file__).parent / 'manifest.json', 'r') as f:
    __version__ = json.load(f)['version']

AUTH_PARAMS = {
    "window_title": "Login to Fanatical" + ("" if not LAZYDOM_MODE else " (Please wait some seconds until the login dialog appears!)"),
    "window_width": 500,
    "window_height": 900,
    "start_uri": HOMEPAGE,
    "end_uri_regex": END_URI_REGEX,
}

LIBRARY_PARAMS = {
    "window_title": "(Re)Scraping Games Window - Wait for Completion Please" + ("" if not LAZYDOM_MODE else " (Please wait some seconds until the process starts)"),
    "window_width": 500,
    "window_height": 900,
    "start_uri": SCRAPING_PAGE,
    "end_uri_regex": END_URI_REGEX,
}

# Open sign-in dialog manages scraping of games after authentication.
SIGNIN_JS=     r'''
        function startAllThis(){
            //window.alert('This is injected javascript from the GOG Galaxy embedded browser (home page)');
            console.log('Embedded Automating Login script launched');
            //if (window.auth_json && window.auth_json.authenticated === true){ 
            //    //window.alert('User is authenticated');
            //    console.log('User is already authenticated, so directly to the scraping page');
            //    window.location.href="'''+SCRAPING_PAGE+r'''"; //goes directly to the scraping page
            //}

            //it seems user is not authenticated, so navigate so proceed simulating cliks to login dialog
            var sideBarTargetNode = document.getElementById('navbar-side');
            if (sideBarTargetNode!=null) {
                //window.alert('Sidebarreference IS present');
                console.log('Sidebarreference Element Was found');
            } //Get reference to the sidebar

            // CallBack function to call when sidebar elements change
            var callbackElementChanged = function(mutationsList, observer){
                //window.alert('DOMSubtreeModified!');
                console.log('DOM element changed!');
                //setTimeout(() => {ScrapePageAndGoToTheNextOne();},500);    // waith that DOM is changed by concurrent call
                completedLogin();
            };

            // Observer Options (describe changes to monitor)
            var config = { attributes: true, childList: true, subtree: true };

            // Monitoring instance binded to callbackfunction (still not armed)
            var observer = new MutationObserver(callbackElementChanged);

            //function to arm the observer on SidebarNode
            function ArmSideBarChangeObservation(){
                // Inizio del monitoraggio del nodo target riguardo le mutazioni configurate
                observer.observe(sideBarTargetNode, config);
            }

            //window.alert('Navbarside has to be  operated to get to login dialog (div opening): here is the HTMLcontent of navbar-side: ' + sideBarTargetNode.innerText);
            //consider the login completed only if userneme element is present in the sidebar
            function completedLogin(){
                if (document.getElementsByClassName('logged-in-as').length>0){
                    observer.disconnect();
                    //window.alert('Elemento di login trovato: '+ document.getElementsByClassName('logged-in-as')[0].textContent);
                    console.log('Elemento di login trovato: '+ document.getElementsByClassName('logged-in-as')[0].textContent);
                    //navigate to library writing cookies and to scrape game names from the page
                    window.location.href="'''+SCRAPING_PAGE+r'''"; 
                    //setTimeout(() =>{window.location.href="'''+SCRAPING_PAGE+r'''";},5000); //wait to start scraping to be sure all cookies are written
                }
            }

            //window.alert('Going to login dialog....');
            console.log('Going to login dialog....');
            // This to open side bar
            document.getElementsByClassName('mobile-nav-button')[0].click();
            //This to open login dialog
            document.getElementsByClassName('sign-in-btn')[0].click();
            //start to track sidebar DOM changes
            ArmSideBarChangeObservation();
        }
'''
INIT_SIGNIN_JS=r'''
        //window.alert('This is injected javascript from the GOG Galaxy embedded browser (sing-in page)');
        var g4_auth_status=window.localStorage.getItem("bsauth");
        var g4_auth_status_value='';
        var startLogin=true;
        //window.alert('LocalStorage autentication status: ' + g4_auth_status);
        if (g4_auth_status){
            g4_auth_status_value= JSON.parse(g4_auth_status).authenticated;
            //window.alert('Current autentication status: ' + g4_auth_status_value.toString());
            if (g4_auth_status_value){
                startLogin=false;
                //window.alert('User is already authenticated, so directly to the scraping page');
                console.log('User is already authenticated, so directly to the scraping page');
                window.location.href="'''+SCRAPING_PAGE+r'''"; //goes directly to the scraping page
            }else{
                console.log('User no more authenticated, proceed with login');
            }

        }else{
            console.log('No old login session present: user not authenticated, proceed with login');
        }
'''

#adds launch logic to script executed on page
if (not LAZYDOM_MODE):
    SIGNIN_JS= INIT_SIGNIN_JS+r'''
            function pollDOM () {
              const el = document.getElementById('navbar-side');
              if (el!=null) {
                startAllThis();
              } else {
                setTimeout(pollDOM, 300); // try again in 300 milliseconds
              }
            }
            if (startLogin){
                //window.alert('Starting Polling dom for navbar-side');
                 pollDOM();
            }
    '''+SIGNIN_JS
else:
    SIGNIN_JS= INIT_SIGNIN_JS+r'''
        console.log('Lazy mode is enabled: waiting 1 seconds before starting auth checks');
        if (startLogin){
            setTimeout(() => { startAllThis(); }, 1000); // just to be quite sure the Ket  is loaded use to navigate to login dialog
        }
    '''+SIGNIN_JS

# manages scraping of games after authentication. Used only to write cookies is SCRAPED_GAMES_MODE is disabled
SCRAPING_JS= r'''
        function startAllThis(){
            console.log('Embedded Library Scraping script launched');
            ''' + ('window.location.href="'+ORDER_PAGE+r'''";
        }''' if not SCRAPED_GAMES_MODE else r'''
                //window.alert('Going to scrape owned games ....');
                console.log('Going to scrape owned games ....');
                var pageNavigationNode=document.getElementsByClassName('algoliaPaginate')[0];
                var pageNavigationElements = Array.from(pageNavigationNode.firstChild.children);
                var numberOfPages= pageNavigationElements.length - 2;
                var numberOfCookies= 1;
                var gamesCookieTemp='';

                //add progress bar 
                var pageFilterContainerNode=document.getElementsByClassName('key-library-filters-container')[0];
                var progress_div = document.createElement('div');
                progress_div.setAttribute('id','myProgress');
                progress_div.setAttribute('style', 'position: relative; width: 100%;height: 30px;background-color: grey');
                var bar_div = document.createElement('div');
                bar_div.setAttribute('id','myBar')
                bar_div.setAttribute('style', 'position: absolute;width: 1%; height: 100%; background-color: green;');
                progress_div.appendChild(bar_div);
                var label_div = document.createElement('div');
                label_div.setAttribute('id','myLabel')
                label_div.setAttribute('style', 'text-align: center; line-height: 30px; color: white;');
                label_div.innerHTML = 'Scraping&nbsp0%';
                bar_div.appendChild(label_div);
                pageFilterContainerNode.appendChild(progress_div);
                //Hide filters
                document.getElementsByClassName('drop-downs-section')[0].hidden=true;
                document.getElementsByClassName('autosearch-container')[0].hidden=true;

                var scraping_Page=1;
                console.log('Number of pages:' + numberOfPages);    
                let allUnrevealedKeyNames=[];

                // Observer Options (what change to monitor)
                var config = { attributes: true, childList: true, subtree: true };

                // Callback Functions used if DOM changes
                var callbackElementChanged = function(mutationsList, observer) {
                    observer.disconnect(); //callback called only once, until rearmed.
                    //window.alert('Change on observed element causes Scape Page callback Called!');
                    console.log('Change on observed element causes Scape Page callback Called!');
                    setTimeout(() => {ScrapePageAndGoToTheNextOne();},500);    // waith that DOM is changed by concurrent call
                };

                // Observer instance to monitor changes that is (linked to callback function)
                var observer = new MutationObserver(callbackElementChanged);

                function WaitForFirstOrderElementToChange(){
                    // Inizio del monitoraggio del nodo target riguardo le mutazioni configurate
                    observer.observe(document.getElementsByClassName('key-list-container')[0].firstChild, config);
                }
                    
                function GetPageUnrevealedKeyNames(){
                    var pageOrderedItems = Array.from(document.getElementsByClassName('order-item-details-container'));
                    let pageUnrevealedKeyNames=[];
                    function addtoUnreveladIfThecase(orderElement){
                        var orderElementName=orderElement.firstChild.firstChild.innerText;
                        if (orderElement.firstChild.nextSibling.firstChild.innerText === 'REVEAL KEY'){
                            pageUnrevealedKeyNames.push(orderElementName);
                            //console.log(orderElementName+ " is unrevealed!"); //debug
                            }
                    };
                    pageOrderedItems.forEach(orderElement => addtoUnreveladIfThecase(orderElement));
                    //console.log('Number of unrevealed elements on pag ' +scraping_Page+ ' is '+ pageUnrevealedKeyNames.length + ' of a total ' +pageOrderedItems.length + ' in this page');
                    return pageUnrevealedKeyNames; 
                }
                
                
                function GotoNextOrder_Page(){
                    //do not use global variable because it causese navigation ... do not know why
                    var pageNavigationElement=document.getElementsByClassName('algoliaPaginate')[0];
                    if (pageNavigationElement){
                        pageNavigationElement.firstChild.lastChild.previousSibling.firstChild.click();
                        return (true)
                    }
                    return(false);
                }

                function ScrapePageAndGoToTheNextOne(){
                        //window.alert('scrapePageAndGoToTheNextOne() Called!');
                        console.log('scrapePageAndGoToTheNextOne() Called!');
                        if (scraping_Page<=numberOfPages){ //Debug only first 3 pages of codes instead of numberOfPages
                            console.log('Scraping Page '+scraping_Page);
                            pageUnrevealedKeyNames=GetPageUnrevealedKeyNames();
                            //currentPageGames=''+ pageUnrevealedKeyNames;
                            //window.alert('GetPageUnrevealedKeyNames.lenght:'+pageUnrevealedKeyNames);
                            if (pageUnrevealedKeyNames.length!=0){
                                currentPageGames=LZString.compressToEncodedURIComponent(''+pageUnrevealedKeyNames);
                                //window.alert(currentPageGames);
                                console.log('currentPageGames '+currentPageGames);
                                console.log('gamesCookieTemp.length+currentPageGames.length '+ (gamesCookieTemp.length+currentPageGames.length));
                                if ((gamesCookieTemp.length+currentPageGames.length) >= 4070){
                                    document.cookie='fanatical_unrev_games_'+numberOfCookies+'=' + gamesCookieTemp;
                                    //window.alert('Written cookie! [fanatical_unrev_games_'+numberOfCookies+'=' + gamesCookieTemp + (gamesCookieTemp.length==0?'':',') +currentPageGames+']');
                                    console.log('Written cookie! [fanatical_unrev_games_'+numberOfCookies+'=' + gamesCookieTemp + (gamesCookieTemp.length==0?'':',') +currentPageGames+']');
                                    numberOfCookies++;
                                    gamesCookieTemp = currentPageGames;
                                }
                                else{
                                    //if (currentPageGames.length!=0) gamesCookieTemp = gamesCookieTemp + (gamesCookieTemp.length==0?'':',') +currentPageGames;
                                    gamesCookieTemp = gamesCookieTemp + (gamesCookieTemp.length==0?'':',') +currentPageGames;
                                }
                                //allUnrevealedKeyNames.push(currentPageGame);//arrays of arrays
                                //allUnrevealedKeyNames=allUnrevealedKeyNames+currentPageGame;//string
                                allUnrevealedKeyNames=allUnrevealedKeyNames.concat(GetPageUnrevealedKeyNames()); //array of elements (Strings as Names of the game)
                            }
                            else{
                                console.log('No unreveled games scraped on page '+scraping_Page);
                            }
                            bar_div.style.width = parseInt(100/numberOfPages*scraping_Page) + '%';
                            label_div.innerHTML = 'Scraping&nbsp'+ parseInt(100/numberOfPages*scraping_Page) +'%';
                            scraping_Page++;
                            WaitForFirstOrderElementToChange(); //rearm next possible scraping if first element changes(this will be done when next page is reloaded)
                            GotoNextOrder_Page();//note that if is the last page the next one will navigate back one page (pcause of pagination bar structure), no harm in this
                        }else{
                            if(gamesCookieTemp.length != 0) {
                                document.cookie= 'fanatical_unrev_games_'+numberOfCookies+'=' + gamesCookieTemp;
                                console.log('Written cookie! [fanatical_unrev_games_'+numberOfCookies+'=' + gamesCookieTemp+']');
                            }
                            //window.alert('Finished Scraping. ('+ allUnrevealedKeyNames.length +') unrevealed games/dlc found: '+ allUnrevealedKeyNames); //debug
                            console.log('Finished Scraping. ('+ allUnrevealedKeyNames.length +') unrevealed games/dlc found: '+ allUnrevealedKeyNames); //debug
                            window.location.href="'''+ORDER_PAGE+r'''"; //make sure that cookies are written in headers and finishes authentication process
                        }
                }                
                
                //start scraping page
                ScrapePageAndGoToTheNextOne();
        }
        ''')

INIT_SCRAPING_JS=r'''
        console.log('This is injected javascript from the GOG Galaxy embedded browser (library page)');
        var LZString=function(){function o(o,r){if(!t[o]){t[o]={};for(var n=0;n<o.length;n++)t[o][o.charAt(n)]=n}return t[o][r]}var r=String.fromCharCode,n="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",e="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_~",t={},i={compressToBase64:function(o){if(null==o)return"";var r=i._compress(o,6,function(o){return n.charAt(o)});switch(r.length%4){default:case 0:return r;case 1:return r+"===";case 2:return r+"==";case 3:return r+"="}},decompressFromBase64:function(r){return null==r?"":""==r?null:i._decompress(r.length,32,function(e){return o(n,r.charAt(e))})},compressToUTF16:function(o){return null==o?"":i._compress(o,15,function(o){return r(o+32)})+" "},decompressFromUTF16:function(o){return null==o?"":""==o?null:i._decompress(o.length,16384,function(r){return o.charCodeAt(r)-32})},compressToUint8Array:function(o){for(var r=i.compress(o),n=new Uint8Array(2*r.length),e=0,t=r.length;t>e;e++){var s=r.charCodeAt(e);n[2*e]=s>>>8,n[2*e+1]=s%256}return n},decompressFromUint8Array:function(o){if(null===o||void 0===o)return i.decompress(o);for(var n=new Array(o.length/2),e=0,t=n.length;t>e;e++)n[e]=256*o[2*e]+o[2*e+1];var s=[];return n.forEach(function(o){s.push(r(o))}),i.decompress(s.join(""))},compressToEncodedURIComponent:function(o){return null==o?"":i._compress(o,6,function(o){return e.charAt(o)})},decompressFromEncodedURIComponent:function(r){return null==r?"":""==r?null:(r=r.replace(/ /g,"+"),i._decompress(r.length,32,function(n){return o(e,r.charAt(n))}))},compress:function(o){return i._compress(o,16,function(o){return r(o)})},_compress:function(o,r,n){if(null==o)return"";var e,t,i,s={},p={},u="",c="",a="",l=2,f=3,h=2,d=[],m=0,v=0;for(i=0;i<o.length;i+=1)if(u=o.charAt(i),Object.prototype.hasOwnProperty.call(s,u)||(s[u]=f++,p[u]=!0),c=a+u,Object.prototype.hasOwnProperty.call(s,c))a=c;else{if(Object.prototype.hasOwnProperty.call(p,a)){if(a.charCodeAt(0)<256){for(e=0;h>e;e++)m<<=1,v==r-1?(v=0,d.push(n(m)),m=0):v++;for(t=a.charCodeAt(0),e=0;8>e;e++)m=m<<1|1&t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t>>=1}else{for(t=1,e=0;h>e;e++)m=m<<1|t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t=0;for(t=a.charCodeAt(0),e=0;16>e;e++)m=m<<1|1&t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t>>=1}l--,0==l&&(l=Math.pow(2,h),h++),delete p[a]}else for(t=s[a],e=0;h>e;e++)m=m<<1|1&t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t>>=1;l--,0==l&&(l=Math.pow(2,h),h++),s[c]=f++,a=String(u)}if(""!==a){if(Object.prototype.hasOwnProperty.call(p,a)){if(a.charCodeAt(0)<256){for(e=0;h>e;e++)m<<=1,v==r-1?(v=0,d.push(n(m)),m=0):v++;for(t=a.charCodeAt(0),e=0;8>e;e++)m=m<<1|1&t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t>>=1}else{for(t=1,e=0;h>e;e++)m=m<<1|t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t=0;for(t=a.charCodeAt(0),e=0;16>e;e++)m=m<<1|1&t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t>>=1}l--,0==l&&(l=Math.pow(2,h),h++),delete p[a]}else for(t=s[a],e=0;h>e;e++)m=m<<1|1&t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t>>=1;l--,0==l&&(l=Math.pow(2,h),h++)}for(t=2,e=0;h>e;e++)m=m<<1|1&t,v==r-1?(v=0,d.push(n(m)),m=0):v++,t>>=1;for(;;){if(m<<=1,v==r-1){d.push(n(m));break}v++}return d.join("")},decompress:function(o){return null==o?"":""==o?null:i._decompress(o.length,32768,function(r){return o.charCodeAt(r)})},_decompress:function(o,n,e){var t,i,s,p,u,c,a,l,f=[],h=4,d=4,m=3,v="",w=[],A={val:e(0),position:n,index:1};for(i=0;3>i;i+=1)f[i]=i;for(p=0,c=Math.pow(2,2),a=1;a!=c;)u=A.val&A.position,A.position>>=1,0==A.position&&(A.position=n,A.val=e(A.index++)),p|=(u>0?1:0)*a,a<<=1;switch(t=p){case 0:for(p=0,c=Math.pow(2,8),a=1;a!=c;)u=A.val&A.position,A.position>>=1,0==A.position&&(A.position=n,A.val=e(A.index++)),p|=(u>0?1:0)*a,a<<=1;l=r(p);break;case 1:for(p=0,c=Math.pow(2,16),a=1;a!=c;)u=A.val&A.position,A.position>>=1,0==A.position&&(A.position=n,A.val=e(A.index++)),p|=(u>0?1:0)*a,a<<=1;l=r(p);break;case 2:return""}for(f[3]=l,s=l,w.push(l);;){if(A.index>o)return"";for(p=0,c=Math.pow(2,m),a=1;a!=c;)u=A.val&A.position,A.position>>=1,0==A.position&&(A.position=n,A.val=e(A.index++)),p|=(u>0?1:0)*a,a<<=1;switch(l=p){case 0:for(p=0,c=Math.pow(2,8),a=1;a!=c;)u=A.val&A.position,A.position>>=1,0==A.position&&(A.position=n,A.val=e(A.index++)),p|=(u>0?1:0)*a,a<<=1;f[d++]=r(p),l=d-1,h--;break;case 1:for(p=0,c=Math.pow(2,16),a=1;a!=c;)u=A.val&A.position,A.position>>=1,0==A.position&&(A.position=n,A.val=e(A.index++)),p|=(u>0?1:0)*a,a<<=1;f[d++]=r(p),l=d-1,h--;break;case 2:return w.join("")}if(0==h&&(h=Math.pow(2,m),m++),f[l])v=f[l];else{if(l!==d)return null;v=s+s.charAt(0)}w.push(v),f[d++]=s+v.charAt(0),h--,s=v,0==h&&(h=Math.pow(2,m),m++)}}};return i}();"function"==typeof define&&define.amd?define(function(){return LZString}):"undefined"!=typeof module&&null!=module&&(module.exports=LZString);
        var g4_auth_status=window.localStorage.getItem("bsauth").trim();
        var g4_auth_status_value='';
        console.log('LocalStorage autentication status: ' + g4_auth_status);
        if (g4_auth_status){
            g4_auth_status_value= JSON.parse(g4_auth_status).authenticated;
            console.log('New autentication status: ' + g4_auth_status_value.toString());
            if (g4_auth_status_value){
                document.cookie='4G_token='+LZString.compressToEncodedURIComponent(g4_auth_status)+';path=/';
                console.log('User authenticad: '+ JSON.parse(g4_auth_status).email);
            }
        }
'''

#adds launch logic to script that will be executed on page
if (not LAZYDOM_MODE):
    SCRAPING_JS=INIT_SCRAPING_JS+r'''
        function pollDOM () {
          console.log('Polling page fo algoliaPaginate element');
          const el = document.getElementsByClassName('algoliaPaginate');
          if (window.auth_json && window.auth_json.authenticated === true && el!=null && el.length>0) { //if pagination element has some childs
            startAllThis();
          } else {
            setTimeout(pollDOM, 300); // try again in 300 milliseconds
          }
        }
        pollDOM();
    '''+SCRAPING_JS
else:
    SCRAPING_JS=INIT_SCRAPING_JS+r'''
        console.log('Lazy mode is enabled: waiting 4 seconds before starting scraping');
        setTimeout(() => { startAllThis(); }, 4000); // just to be quite sure the Key list is loaded use to navigate to login dialog
    '''+SCRAPING_JS


#Used to let the user choice to skip authentication. Used only to debug without getting games from fanatical but closing login dialog and getting them from NOAUTH_DEBUGMODE_DATAFILE
NOAUTH_DEBUGMODE_JS=r'''
    if(window.confirm('Simulate Authentication?')){
       window.location.href="'''+BUNDLE_PAGE+r'''";
    }
'''

#Used to close cookie policy
ACCEPT_COOKIE_POLICY_JS=r'''
            function getCookie(cname) {
              var name = cname + "=";
              var decodedCookie = decodeURIComponent(document.cookie);
              var ca = decodedCookie.split(";");
              for(var i = 0; i <ca.length; i++) {
                var c = ca[i];
                while (c.charAt(0) == ' ') {
                  c = c.mappingring(1);
                }
                if (c.indexOf(name) == 0) {
                  return c.mappingring(name.length, c.length);
                }
              }
              return "";
            }
            if(getCookie('CookieConsent')===""){
                //window.alert(document.getElementsByClassName('accept-cookies-btn')[0].innerText);
                // This to close accept (navigation is anyway possibile with jscode, so no problem to let this in "to be accepted state"
                document.getElementsByClassName('accept-cookies-btn')[0].click();
            }
'''

#This is the structure used to declare JS script injection in NextStep function
INJECTED_JS_CATALOG = {
               HOMEPAGE_URI_REGEX: [SIGNIN_JS],
               SCRAPING_URI_REGEX: [SCRAPING_JS]
               }


#Add cookie policy closure to Homepage JS if CLOSE_COOKIEPOLICYCONSENT is set to true
if(CLOSE_COOKIEPOLICYCONSENT):
    INJECTED_JS_CATALOG[HOMEPAGE_URI_REGEX][0] = ACCEPT_COOKIE_POLICY_JS + INJECTED_JS_CATALOG[HOMEPAGE_URI_REGEX][0]


#Add optional navigation to non authenticated page as an authorization simulation on Homepage
if (NOAUTH_DEBUGMODE):
    AUTH_PARAMS["end_uri_regex"]=END_URI_REGEX_NOAUTH_DEBUG
    LIBRARY_PARAMS["end_uri_regex"]=END_URI_REGEX_NOAUTH_DEBUG
    INJECTED_JS_CATALOG[HOMEPAGE_URI_REGEX][0] = NOAUTH_DEBUGMODE_JS + INJECTED_JS_CATALOG[HOMEPAGE_URI_REGEX][0]

_games_update_running= False #global variable used as a traffic light to avoid multiple updates to run at the same time.

logger = logging.getLogger(__name__) #gets the deafault global logger
logger.setLevel(MIN_LOG_LEVEL)

class FanaticalPlugin(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(
            Platform.Fanatical,
            __version__,
            reader,
            writer,
            token
        )
        logger.info('[Fanatical Plugin] SCRAPED_GAMES_MODE %s',SCRAPED_GAMES_MODE)
        #logger.debug('[Fanatical Plugin] Scraping JS %s',SCRAPING_JS) #used to debug javascript composition
        #logger.debug('[Fanatical Plugin] Signin JS %s',SIGNIN_JS) #used to debug javascript composition
        logger.info('[Fanatical Plugin] NOAUTH_DEBUGMODE %s',NOAUTH_DEBUGMODE)
        self.http_client = HTTPClient(self.store_credentials)
        self.session_cookie = None
        self.games_scraped = [] # void list declaration also manages the case of "no key in library" when scraped gamed mode is used.
        self._owned_games_cache = [] # void cache declaration also manages the case of "no game in cache" 
        self._owned_games_last_updated = datetime.now()
        self._update_owned_games_ongoing= False
        self.games_just_scraped= False
        
    async def shutdown(self):
        await self.http_client.close()


    def injectCredentialsString(self,credentials='{authenticated: false}'):
        return r'''
        console.log('Current autentication status: ' + window.localStorage.getItem("bsauth"));
        window.localStorage.setItem('bsauth', ' ''' +credentials+r''' ');
        console.log('After injection autentication status: ' + window.localStorage.getItem("bsauth"));
        '''

    # implement methods
    async def authenticate(self, stored_credentials=None):
        if not stored_credentials:
            logger.info('[Fanatical Plugin] plugin/authenticate: no stored credentials')
            return NextStep("web_session", AUTH_PARAMS, cookies=None, js=INJECTED_JS_CATALOG) #open dialog on homepage and let login dialog is opened via JS (going directly to homepage causes user creation dialog to appear)

        logger.debug('[Fanatical Plugin] stored_credentials exists:%s', stored_credentials)

        # preprares the http client with the existing credentials/cookies
        self.http_client.update_cookies(stored_credentials)
        #credentialDict= json.loads(stored_credentials)
      
        try:
            # If scraped games mode is on the only way to get games from web is to open the embedded browser in any case and analyze the rendered DOM
            # TODO try to access library if crediantial let access them (the browser shoud redirect to home page if not auth)
            if (SCRAPED_GAMES_MODE):
                logger.debug('[Fanatical Plugin] try to get directly to the library and (re)scrape games')
                NEW_INJECTED_JS_CATALOG =  INJECTED_JS_CATALOG.copy()
                NEW_INJECTED_JS_CATALOG[HOMEPAGE_URI_REGEX][0] = self.injectCredentialsString(lzstring.LZString().decompressFromEncodedURIComponent(stored_credentials['4G_token'])) + INJECTED_JS_CATALOG[HOMEPAGE_URI_REGEX][0] # add authorization to LocalStorage in this case
                #logger.debug('[Fanatical Plugin] Signin JS %s',NEW_INJECTED_JS_CATALOG[HOMEPAGE_URI_REGEX][0]) #used to debug javascript composition
                #return NextStep("web_session", LIBRARY_PARAMS, cookies=self.http_client.get_next_step_cookies(), js=NEW_INJECTED_JS_CATALOG)# go to pass login6
                return NextStep("web_session", AUTH_PARAMS, cookies=self.http_client.get_next_step_cookies(), js=NEW_INJECTED_JS_CATALOG)# go to pass login

            if (NOAUTH_DEBUGMODE):# only if SCRAPED_GAMES_MODE is not enable
                logger.debug('[Fanatical Plugin] NOAUTH_DEBUGMODE simulating test user login')
                return Authentication('debuguser@test.com','debuguser@test.com') #Send to GG that user is authenticated (gog is connected)

            # If NO Scraping Mode is enabled and credentials exist then you're probably authenticated
            logger.debug('[Fanatical Plugin] getting athentication token from credentials to access API')
            auth_data_json=json.loads(lzstring.LZString().decompressFromEncodedURIComponent(stored_credentials['4G_token']))
            self.http_client.auth_token = auth_data_json['token']
            logger.debug('[Fanatical Plugin] Authentication SUCCESSFULL using stored credentials')
            return Authentication(auth_data_json['_id'],auth_data_json['email'])

        except:
            logger.warning('[Fanatical Plugin] Authentication FAILED exception while managing old credentials - restarting clearing credentials')
            return NextStep("web_session", AUTH_PARAMS, cookies=None, js=INJECTED_JS_CATALOG) #clear out credentials


  
    def filter_cookies(self, cookies):    
        filtered_cookies={}
        for cookie in cookies:
            logger.debug('[Fanatical Plugin] Checking cookie: %s',cookie)
            if cookie['name']:
                if (cookie['name'][0:22] == 'fanatical_unrev_games_'):
                    logger.debug('[Fanatical Plugin] Cookie: %s was filterend and will not be stored as credentials',cookie['name'])
                    continue 
                filtered_cookies[cookie['name']]=cookie['value']
        return filtered_cookies #{cookie['name']: cookie['value'] for cookie in cookies if cookie['name']}

    #called when auth dialog/next page is closed, with all cookies of the new page filled-in
    async def pass_login_credentials(self, step, credentials, cookies):
        logger.debug('[Fanatical Plugin] pass_login_credentials START')
        session_cookies = self.filter_cookies(cookies) #{cookie['name']: cookie['value'] for cookie in cookies if cookie['name']}
        self.http_client.update_cookies(session_cookies)
        logger.debug('[Fanatical Plugin] pass_login_credentials %s', session_cookies)
        try:
            return await self.get_user_info_cookies(cookies, credentials) # crediantials is now the exting url on witch cookies are captured, and is not used anymore as credential
        except AuthenticationRequired:
            logger.info('[Fanatical Plugin] Trying to navigate to an authenticated page')
            return NextStep("web_session", AUTH_PARAMS, cookies=self.http_client.get_next_step_cookies(), js=INJECTED_JS_CATALOG) # loop to login page with updated cookies

    async def get_user_info_cookies(self,cookies, credentials):
        logger.debug('[Fanatical Plugin] get_user_info_cookie CALLED! with cookies on page: %s', credentials)
        username='unknown_user'
        self.games_scraped=[] # for SCRAPING MODE avoids games that are no more present will remain in list if authentication happens, rebuilkding the list form scratch
        if (NOAUTH_DEBUGMODE):
            logger.info('[Fanatical Plugin] NOAUTH_DEBUGMODE simulating test user login')
            return Authentication('debuguser@test.com','debuguser@test.com') #Send to GG that user is authenticated (gog is connected)
        #username is in cookie information, placed there by Javacript function! It works as cookies are passed form one page to the other.
        for cookie in cookies:#first loop to retrieve cookie values
            if (cookie['name'] == '4G_token'): #and cookie['path']=='/en'
                try:
                    logger.debug('[Fanatical Plugin] get_user_info_cookie 4G_token: %s, path[%s]', cookie['value'],cookie['path'])
                    #logger.debug('[Fanatical Plugin] decompresses 4G_token: %s', lzstring.LZString().decompressFromEncodedURIComponent(cookie['value']))
                    auth_data_json=json.loads(lzstring.LZString().decompressFromEncodedURIComponent(cookie['value']))
                    logger.debug('[Fanatical Plugin] 4G_token username: %s', auth_data_json['email'])
                    username = auth_data_json['email']
                    logger.debug('[Fanatical Plugin] 4G_token user_id: %s', auth_data_json['_id'])
                    user_id = auth_data_json['_id']
                    logger.debug('[Fanatical Plugin] 4G_token token: %s', auth_data_json['token'])
                    self.http_client.auth_token=cookie['value']=auth_data_json['token']
                except:
                    logger.warning('[Fanatical Plugin] Error while parsin auth cookie')
                    #self.http_client.update_cookies({"4G_token":"","4G_bsauth":""})
                    raise AuthenticationRequired
            
            #this get games/renew games each time authentication happens. It is the only way to gatre games in scraping mode.
            if SCRAPED_GAMES_MODE and cookie['name'][0:22] == 'fanatical_unrev_games_':
                logger.debug('[Fanatical Plugin] cookie %s has value %s', cookie['name'],cookie['value'])
                scraped_unrev_games_pages=cookie['value'].split(',') #comma separates different compressed pages
                logger.debug('[Fanatical Plugin] number of scraped pages in cookie is %s',len(scraped_unrev_games_pages))
                for scraped_page in scraped_unrev_games_pages:
                    logger.debug('[Fanatical Plugin] scraped page contents ['+scraped_page+']')
                    logger.debug('[Fanatical Plugin] decompressed page ['+lzstring.LZString().decompressFromEncodedURIComponent(scraped_page)+']')
                    self.games_scraped.extend((lzstring.LZString().decompressFromEncodedURIComponent(scraped_page)).split(',')) #add to list
                #scraped_unrev_games= cookie['value']
                #self.games_scraped.extend(scraped_unrev_games.split(','))
                logger.debug('[Fanatical Plugin] # of games_scraped so far: %s', len(self.games_scraped)) #';'.join(self.games_scraped)

        if SCRAPED_GAMES_MODE:
            self.games_just_scraped=True
        if (username!='unknown_user' and self.http_client.auth_token != ''): #minimal condition to be met to be considered authenticated
            logger.info('[Fanatical Plugin] Authentication SUCCESSFULL')
            return Authentication(user_id,username)
        logger.info('[Fanatical Plugin] Authentication FAILED No authentication cookie found...loop in Authentication')
        raise AuthenticationRequired # auth do not siceeded, so loop going to home page and launching JS login script.

    async def get_owned_games(self): #put Games in cache
        self._update_owned_games_ongoing=True
        # if (CACHEING_GAMES_FLAG):
        #     if (self._owned_games_cache is None): #Get All games from original source the first time. 
        #         self._owned_games_cache = await self._get_owned_games_from_fanatical() #Updatecache
        #     self._update_owned_games_ongoing=False
        #     return self._owned_games_cache #list(self._owned_games_cache.values()) 
        # else:
        #     not_cached_games= await self._get_owned_games_from_fanatical() #no cacheing
        #     self._update_owned_games_ongoing=False
        #     return not_cached_games #no cacheing
        owned_games= await self._get_owned_games_from_fanatical() #no cacheing
        if (CACHEING_GAMES_FLAG):
            self._owned_games_cache=owned_games
        self._update_owned_games_ongoing=False
        return owned_games 


    async def _get_owned_games_from_fanatical(self):
        #using HTML as source of HTLML does not work because of react usage!
        #so reading if from DOM with javascrit when authenticated and write to cookies (browser side) so to read (plugin side) when authentication is fineshed
        logger.debug('[Fanatical Plugin] getting owned games')
        games = [] # manges the case when no games are in library

        if (SCRAPED_GAMES_MODE): # returning scraped games
            logger.debug('[Fanatical Plugin] returning owned games last scraped from library page:' + ';'.join(self.games_scraped))
            games.extend(self.parse_games_into_gog_games(self.games_scraped)) #functioning with scraped_games
            self._owned_games_last_updated = datetime.now()
            return games #functioning with scraped_games

        #getting games json data (local if NOAUTH_DEBUGMODE or the real remote one)
        if (NOAUTH_DEBUGMODE):
                logger.debug('[Fanatical Plugin] NOAUTH_DEBUGMODE returning owned games from Local Games Data')
                try:
                    debug_data_path=os.path.dirname(os.path.realpath(__file__))+ '\\' + NOAUTH_DEBUGMODE_DATAFILE
                    logger.debug('[Fanatical Plugin] Opening Local Games Data file: ' + debug_data_path)
                    f = open( debug_data_path, 'r')
                    json_data=f.read()
                    logger.debug('[Fanatical Plugin] json part first 20 chars'+ json_data[0:20])
                except:
                    logger.warning('[Fanatical Plugin] NOAUTH_DEBUGMODE Exception raised reading Game List from file '+ debug_data_path +'. Returning empty game list')
                    json_data='[]'
                finally:
                    f.close()
        else:
            try:
                HEADERS = {
                        "authorization": self.http_client.auth_token
                }
                logger.debug('[Fanatical Plugin] Getting json of keys for the authenticated user')
                json_data = await self.http_client.get(KEYS_URL,additionalHeaders=HEADERS)# getkeys json
                logger.debug('[Fanatical Plugin] json part first 20 chars'+ json_data[0:20])
            except AuthenticationRequired:
                logger.warning('[Fanatical Plugin] authentication lost while getting keys from fanatical')
                self.lost_authentication()
                raise

        #parsing games json data in to games list
        try:
            gamesList= json.loads(json_data)
        except:
            logger.error('[Fanatical Plugin] malformed json game list')
            raise

        logger.debug('[Fanatical Plugin] json loaded in memory data model')

        if BACKUP_GAMES_DB:
            try:
                with open(debug_data_path+'_last.json', 'w') as outfile:
                    json.dump(gamesList, outfile, indent=4)
            except:
                logger.warning('[Fanatical Plugin] Exception while writing BACKUP_GAMES_DB')

        games.extend(self.extract_valid_unrevealed_keys(gamesList))
        self._owned_games_last_updated = datetime.now()
        logger.debug('[Fanatical Plugin] returning games from json loaded in memory data model (Fanatical or BACKUP_GAMES_DB )')

        return games

    def parse_games_into_gog_games(self, games):
    # used only for scraped games mode, so no filtering on revealed games because already done on javascript side
        logger.debug('[Fanatical Plugin] parse_scraped_games_into_gog_games')
        mapping_dict= self.get_fanatical_game_specials_mapping()
        for game in games:
            game_name = self.map_fanatical_game_specials_mapping(game, mapping_dict)
            if self.check_exclusion(game_name):
                logger.info('[Fanatical Plugin] Scraped Game %s Discarded (DLC or Package)', game_name)
                continue
            url_slug = self.get_url_slug_name(game_name)
            logger.debug('[Fanatical Plugin] Parsed Scraped Game is  %s, %s', game_name, url_slug)
            yield Game(
                game_id=url_slug,
                game_title=game_name,
                license_info=LicenseInfo(LicenseType.SinglePurchase),
                dlcs=[]
            )

    def get_fanatical_game_specials_mapping(self):
    # Read persistent rules dictionary to map fanatical games to more common one (used by GOG to get metadata etc)
        game_specials_data_path=os.path.dirname(os.path.realpath(__file__))+ '\\' + GAMES_SPECIALS_DATAFILE
        logger.debug('[Fanatical Plugin] loading Games Specials Mapping data from file ' + game_specials_data_path)
        try:
            logger.debug('[Fanatical Plugin] Opening file...')
            f = open( game_specials_data_path, 'r')
            json_data=f.read()
            logger.debug('[Fanatical Plugin] json part first 20 chars'+ json_data[0:20])
        except:
            logger.warning('[Fanatical Plugin] Exception raised reading Games Specials JsonData from file '+ game_specials_data_path +' NO game name or exclusion rules will be applied!!')
            json_data='[]' # simulates empty rules dictionary if file not found (or in case of other exceptions)
        finally:
            f.close()
        return json.loads(json_data)

    @staticmethod
    def map_fanatical_game_specials_mapping(game_name, mapping):
    # Use persistent rules dictionary to map fanatical games to more common one (used by GOG to get metadata etc)
        new_name=game_name
        for game in mapping.keys():
            if game_name.rfind(game)>=0:
                new_name= mapping[game]
                logger.info('[Fanatical Plugin] Libraray Game %s Was Mapped to %s basing on mapping game name rules', game_name, new_name)
        return new_name

    @staticmethod
    def get_url_slug_name(game_name):
        temp_name=re.sub('[^A-Za-z0-9 ]+', '', game_name)
        temp_name=re.sub(' +', ' ', temp_name).strip()
        temp_name=re.sub(' ', '-', temp_name).strip()
        return temp_name.lower() #game['_id']

    @staticmethod
    def check_exclusion(game_name):
        if (game_name.rfind('__FORCE_EXCLUSION__')>=0):
            return True
        #if ((game_name.lower()).rfind('dlc')>=0):
        #    return True
        #if (game['name'].lower()).rfind(' pack')):
        #        return True
        
    def extract_valid_unrevealed_keys(self, gameList):
    # Used only by json (not scraping) mode. No filtering on revealed games was previously performed 
        logger.debug('[Fanatical Plugin] get_account_keys CALLED!')
        mapping_dict= self.get_fanatical_game_specials_mapping() #reread each time it is called, so mapping rules are changed eche time function is called
        for game in gameList:
            if (game['status']=='fulfilled'):
                game_name = self.map_fanatical_game_specials_mapping(game['name'],mapping_dict)
                if self.check_exclusion(game_name):
                    logger.info('[Fanatical Plugin] Libraray Game %s Was Discarded basing on mapping game name rules', game_name)
                    continue
                url_slug = self.get_url_slug_name(game_name) #game['_id'] usid id produces unknown games (mistery :-) ) 
                logger.debug('[Fanatical Plugin] Parsed Game is  %s, %s', game_name, url_slug)
                yield Game(
                    game_id=url_slug,
                    game_title=game_name,
                    license_info=LicenseInfo(LicenseType.SinglePurchase),
                    dlcs=[]
                )

    async def _update_owned_games(self):
        logger.debug('[Fanatical Plugin] getting updated games')
        self._update_owned_games_ongoing=True
        owned_games = await self._get_owned_games_from_fanatical() #get already scraped or re-read from json

        for game in (self._owned_games_cache):
             if game not in owned_games:
                logger.info('[Fanatical Plugin] game was removed because removed from source:' + game.game_title)
                self.remove_game(game.game_id)

        for game in (owned_games):
             if game not in self._owned_games_cache:
                logger.info('[Fanatical Plugin] new game added because added to source:' + game.game_title)
                self.add_game(game)
        
        if (CACHEING_GAMES_FLAG):
            self._owned_games_cache = owned_games
        self._owned_games_last_updated = datetime.now()
        logger.debug('[Fanatical Plugin] cache not valid - games updated')
        self._update_owned_games_ongoing=False

    def tick(self):
        #logger.debug('[Fanatical Plugin] tick after %s, when empty cache is %s',datetime.now() - self._owned_games_last_updated, self._owned_games_cache is not None)
        #if (self._owned_games_cache is not None): #to use when games are not still read from source at least one time
        # in scraping mode consider cache timed out if games was just scraped
            if ((datetime.now() - self._owned_games_last_updated) < OWNED_GAMES_CACHE_TIMEOUT and not self.games_just_scraped):
                return
            if self.games_just_scraped:
                self.games_just_scraped=False #in scraping mode from now to the next scraping games are no more considered "just scraped"
                logger.debug('[Fanatical Plugin] forcing update of just scraped games')
            else:
                logger.debug('[Fanatical Plugin] cache of owned games timed out')

            if not self._update_owned_games_ongoing:
                asyncio.create_task(self._update_owned_games())
            else:
                self._owned_games_last_updated += timedelta(seconds=60)
                logger.debug('[Fanatical Plugin] cache refresh still running, wait 60 seconds before repeating')
                                
def main():
    create_and_run_plugin(FanaticalPlugin, sys.argv)


# run plugin event loop
if __name__ == "__main__":
    main()
