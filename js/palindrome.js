let word="madam";
let arr=word.split('');
let reverse=arr.reverse();
let reverseword=reverse.join('');

if(word==reverseword){
    console.log("string is palindrome");

}else{
    console.log("string not palindrome");
}