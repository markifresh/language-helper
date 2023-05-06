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
  if (document.getElementsByTagName('audio').length != 0)
    return null
  
  let newAudio = document.createElement("audio");
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
  let fileName = "ATTS " + cont.innerText.replace(/\u00A0/g, " ").trim();
  fileName = fileName.endsWith('.') ? fileName + 'mp3' : fileName + '.mp3';
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