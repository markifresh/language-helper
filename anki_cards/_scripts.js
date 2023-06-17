var audioPrefix = "ATTS ";
var audioExtension = "mp3";

function compare_text(text1, text2){
    let text = text1;
    let input = text2;
    if (text.length < input.length)
      text += ' '.repeat(input.length - text.length);       
    
    let highlightedText = "";
    
    for (let i = 0; i < text.length; i++) {
      if (i >= input.length)
        highlightedText += "<span class='highlight'>" + ' ' + "</span>";
      
      else{
        if (input[i] !== text[i])
          highlightedText += "<span class='highlight'>" + input[i] + "</span>";
        else
          highlightedText += input[i];
      }
    }

    return highlightedText;
}


function create_audio(fileName, autoplay=true){
  if (document.getElementById('wordAudio').length != 0)
    return null
  
  let newAudio = document.createElement("audio");
  newAudio.Id = "wordAudio";
  newAudio.controls = true;
  newAudio.src = fileName;
  if (autoplay){
    newAudio.autoplay = true;
    newAudio.play();
  }
  return newAudio;
}

function make_audio_filename(elementID) {
  let cont = document.getElementById(elementID);
  let fileName = audioPrefix + cont.innerText.replace(/\u00A0/g, " ").trim();
  fileName = fileName.endsWith('.') ? fileName + audioExtension : fileName + '.' + audioExtension;
  return fileName;
}

function append_audio_to(elementID, audio){
  let destination = document.getElementById(elementID);
  destination.appendChild(audio);
}

function make_audio(nameSource, destinationElement, autoplay=true){
  let fileName = make_audio_filename(nameSource);
  let audioObj = create_audio(fileName, autoplay);
  if(audioObj)
    append_audio_to(destinationElement, audioObj);
}

function make_input(){
  if (document.getElementsByTagName('input'))
   return null;

  var input_box = document.createElement("input");
  input_box.id = 'input_box';
  input_box.type = 'text';
  return input_box;
}

function appendSentenceDiv(sentence, word, elementID) {
  let targetElement = document.createElement(elementID);
  if (sentence && !targetElement.innerText){
    let spanStyle = 'background-color: yellow';
    const regex = new RegExp(`(${word})`, "gi");
    const highlightedSentence = sentence.replace(regex, "<span style='" + spanStyle + "'>$1</span>");
    const newDiv = document.createElement("div");
    newDiv.innerHTML = highlightedSentence;
    newDiv.style.color = 'darkgrey';
    document.getElementById(elementID).appendChild(newDiv);
  }}

function toggleClass(elementID, className) {
  document.getElementById(elementID).classList.toggle(className)  
}

function createPlayButton(parentElementId, audioSourceElement){
  let playIconStr = '<svg xmlns="http://www.w3.org/2000/svg" height="25" viewBox="0 -960 960 960" width="25">' +
                    '<path d="M320-203v-560l440 280-440 280Zm60-280Zm0 171 269-171-269-171v342Z"/>'+
                  '</svg>';
  let pauseIconStr = '<svg xmlns="http://www.w3.org/2000/svg" height="25" viewBox="0 -960 960 960" width="25">'+
                    '<path d="M525-200v-560h235v560H525Zm-325 0v-560h235v560H200Zm385-60h115v-440H585v440Zm-325 '+
                             '0h115v-440H260v440Zm0-440v440-440Zm325 0v440-440Z"/>' +
                  '</svg>';
  // create audio
  let newAudio = document.createElement("audio");
  newAudio.Id = "sentenceAudio";
  newAudio.controls = false;
  newAudio.autoplay = false;
  newAudio.src = make_audio_filename(audioSourceElement);
  
  let newBtn = document.createElement('button');
  newBtn.id = 'sentencePlayBtn';
  newBtn.classList = 'btn btn-primary round-button';
  newBtn.innerHTML =  playIconStr;
  newBtn.style.margin = '0';
  newBtn.style.padding = '0';
  newBtn.style.display = 'contents';

  let parentElemen = document.getElementById(parentElementId);
  parentElemen.appendChild(newAudio);
  parentElemen.appendChild(newBtn);

  newBtn.addEventListener('click',function(e) {
    newBtn.classList.toggle('is_playing');
    if(newBtn.classList.contains('is_playing')){
      newBtn.innerHTML =  pauseIconStr;
      newAudio.play();
    }
    else{
      newBtn.innerHTML =  playIconStr;
      newAudio.pause();
    }  
  });

  newAudio.addEventListener('ended', function(){
    newBtn.classList.toggle('is_playing');
    newBtn.innerHTML =  playIconStr;
  })
}

// Test adding multiple source with different format and prefixes
//   This example includes multiple <source> elements. The browser tries to load the first source 
// element (Opus) if it is able to play it; if not it falls back to the second (Vorbis) 
// and finally back to MP3:
// <audio controls>
//   <source src="foo.opus" type="audio/ogg; codecs=opus" />
//   <source src="foo.ogg" type="audio/ogg; codecs=vorbis" />
//   <source src="foo.mp3" type="audio/mpeg" />
// </audio>