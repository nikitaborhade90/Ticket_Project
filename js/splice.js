const arr=[1,2,3,4,5,6,7]
const removed=arr.splice(1,2)
console.log("element removed",removed)
console.log("array after removal",arr)
arr.splice(1,0,20,30)
console.log("array after insert ",arr)
arr.splice(2,1,3)
console.log("array after replace",arr)